from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.accounts.permissions import is_quality_or_admin
from apps.catalog.models import MedicalProduct, ProductVariant

from .audit import log_action
from .models import FMEAItem, FMEARevision, ItemStatus, RevisionStatus


def next_version(product: MedicalProduct, variant: ProductVariant | None = None) -> str:
    versions = FMEARevision.objects.filter(product=product, variant=variant).values_list(
        "version", flat=True
    )
    parsed = []
    for value in versions:
        try:
            major, minor = (int(part) for part in str(value).split(".", 1))
        except (TypeError, ValueError):
            continue
        parsed.append((major, minor))
    if not parsed:
        return "1.0"
    major, minor = max(parsed)
    return f"{major}.{minor + 1}"


def _ensure_status(revision: FMEARevision, *allowed: str) -> None:
    if revision.status not in allowed:
        allowed_titles = ", ".join(dict(RevisionStatus.choices)[item] for item in allowed)
        raise ValidationError(
            {
                "detail": (
                    f"Недопустимый переход из статуса «{revision.get_status_display()}». "
                    f"Допустимо: {allowed_titles}"
                )
            }
        )


def ensure_revision_editable(revision: FMEARevision, user: User) -> None:
    if revision.status in (RevisionStatus.APPROVED, RevisionStatus.ARCHIVED):
        raise PermissionDenied("Утверждённая или архивная ревизия доступна только для чтения")
    if revision.status == RevisionStatus.REVIEW and not is_quality_or_admin(user):
        raise PermissionDenied(
            "На этапе проверки правки доступны менеджеру по качеству или администратору"
        )


def _snapshot(revision: FMEARevision) -> dict:
    return {
        "product_id": revision.product_id,
        "variant_id": revision.variant_id,
        "version": revision.version,
        "status_before": revision.status,
    }


@transaction.atomic
def create_revision(
    *,
    product: MedicalProduct,
    user: User,
    variant: ProductVariant | None = None,
    version: str | None = None,
    change_reason: str = "",
    based_on: FMEARevision | None = None,
    request=None,
    audit: bool = True,
) -> FMEARevision:
    if variant is not None and variant.product_id != product.pk:
        raise ValidationError({"variant": "Исполнение должно принадлежать выбранному изделию"})
    if based_on is not None and based_on.product_id != product.pk:
        raise ValidationError({"based_on": "Базовая ревизия должна относиться к тому же изделию"})

    version = version or next_version(product, variant)
    try:
        revision = FMEARevision.objects.create(
            product=product,
            variant=variant,
            version=version,
            status=RevisionStatus.DRAFT,
            based_on=based_on,
            change_reason=change_reason,
            created_by=user,
        )
    except IntegrityError as exc:
        raise ValidationError(
            {"version": "Ревизия с такой версией уже существует для выбранного изделия/исполнения"}
        ) from exc

    if audit:
        log_action(
            user=user,
            action="create",
            entity=revision,
            payload={**_snapshot(revision), "change_reason": change_reason},
            request=request,
        )
    return revision


@transaction.atomic
def clone_revision(
    *,
    source: FMEARevision,
    user: User,
    version: str | None = None,
    change_reason: str = "",
    request=None,
) -> FMEARevision:
    _ensure_status(
        source, RevisionStatus.DRAFT, RevisionStatus.REVIEW, RevisionStatus.APPROVED
    )

    target = create_revision(
        product=source.product,
        variant=source.variant,
        user=user,
        version=version,
        change_reason=change_reason or f"Копия ревизии {source.version}",
        based_on=source,
        request=request,
        audit=False,
    )

    mapping = {}
    for item in source.items.all():
        cloned = FMEAItem.objects.create(
            revision=target,
            component=item.component,
            failure_mode=item.failure_mode,
            failure_cause=item.failure_cause,
            failure_effect=item.failure_effect,
            severity=item.severity,
            occurrence=item.occurrence,
            detection=item.detection,
            recommended_action=item.recommended_action,
            responsible=item.responsible,
            due_date=item.due_date,
            status=ItemStatus.OPEN,
            source=item.source,
            source_reference=item.source_reference,
            created_by=user,
        )
        mapping[item.pk] = cloned

    for dependency in source.dependencies.all():
        source_item = mapping.get(dependency.source_item_id)
        target_item = mapping.get(dependency.target_item_id)
        if source_item and target_item:
            target.dependencies.create(
                source_item=source_item,
                target_item=target_item,
                relation_type=dependency.relation_type,
                description=dependency.description,
            )

    log_action(
        user=user,
        action="clone",
        entity=target,
        payload={**_snapshot(target), "source_revision_id": source.pk},
        request=request,
    )
    return target


@transaction.atomic
def submit_review(*, revision: FMEARevision, user: User, request=None) -> FMEARevision:
    _ensure_status(revision, RevisionStatus.DRAFT)
    if not revision.items.exists():
        raise ValidationError({"detail": "Нельзя отправить на проверку пустую ревизию"})

    before = _snapshot(revision)
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action="submit",
        entity=revision,
        payload=before,
        request=request,
    )
    return revision


def _validate_items(revision: FMEARevision) -> None:
    invalid = []
    for item in revision.items.all():
        blank = not (
            item.failure_mode.strip()
            and item.failure_cause.strip()
            and item.failure_effect.strip()
        )
        out_of_range = not all(
            1 <= value <= 10 for value in (item.severity, item.occurrence, item.detection)
        )
        if blank or out_of_range:
            invalid.append(item.pk)
    if invalid:
        raise ValidationError(
            {
                "detail": (
                    "Ревизия содержит незаполненные или некорректные пункты FMEA: "
                    + ", ".join(str(pk) for pk in invalid)
                )
            }
        )


@transaction.atomic
def approve_revision(*, revision: FMEARevision, user: User, request=None) -> FMEARevision:
    _ensure_status(revision, RevisionStatus.REVIEW)
    _validate_items(revision)

    before = _snapshot(revision)
    revision.status = RevisionStatus.APPROVED
    revision.approved_by = user
    revision.approved_at = timezone.now()
    revision.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
    log_action(
        user=user,
        action="approve",
        entity=revision,
        payload=before,
        request=request,
    )
    return revision


@transaction.atomic
def reject_revision(
    *, revision: FMEARevision, user: User, reason: str, request=None
) -> FMEARevision:
    _ensure_status(revision, RevisionStatus.REVIEW)
    if not (reason or "").strip():
        raise ValidationError({"reason": "Укажите причину отклонения"})

    before = _snapshot(revision)
    revision.status = RevisionStatus.DRAFT
    revision.change_reason = reason.strip()
    revision.save(update_fields=["status", "change_reason", "updated_at"])
    log_action(
        user=user,
        action="reject",
        entity=revision,
        payload={**before, "reason": reason.strip()},
        request=request,
    )
    return revision


@transaction.atomic
def archive_revision(*, revision: FMEARevision, user: User, request=None) -> FMEARevision:
    _ensure_status(revision, RevisionStatus.DRAFT, RevisionStatus.APPROVED)
    before = _snapshot(revision)
    revision.status = RevisionStatus.ARCHIVED
    revision.save(update_fields=["status", "updated_at"])
    log_action(
        user=user,
        action="archive",
        entity=revision,
        payload=before,
        request=request,
    )
    return revision
