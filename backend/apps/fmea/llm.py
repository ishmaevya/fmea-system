from hashlib import sha256

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.accounts.permissions import is_quality_or_admin
from apps.catalog.models import Component

from .audit import log_action
from .models import (
    FMEAItem,
    FMEARevision,
    ItemSource,
    LLMSuggestion,
    SuggestionStatus,
)
from .services import ensure_revision_editable

PROVIDER = "stub"
MODEL_NAME = "rule-based-demo-v1"


def build_prompt(revision: FMEARevision, component: Component, hints: str = "") -> str:
    parts = [
        "Сформируйте демонстрационные варианты отказа для компонента изделия.",
        f"Компонент: {component.code} — {component.name}.",
        f"Ревизия: {revision.version}.",
    ]
    if hints:
        parts.append(f"Дополнительный контекст: {hints}")
    return "\n".join(parts)


def build_response(component: Component) -> dict:
    digest = sha256(component.code.encode("utf-8")).digest()
    return {
        "disclaimer": "Демонстрационная заглушка на правилах, не реальная языковая модель.",
        "suggestions": [
            {
                "failure_mode": f"Отказ компонента {component.code}",
                "failure_cause": f"Потенциальный дефект или износ элемента {component.code}",
                "failure_effect": (
                    f"Нарушение функции компонента {component.code} в составе изделия"
                ),
                "severity": 5 + digest[0] % 6,
                "occurrence": 2 + digest[1] % 5,
                "detection": 3 + digest[2] % 5,
                "recommended_action": (
                    "Проверить проектную документацию и добавить контроль параметра"
                ),
                "source_reference": "Демонстрационная LLM-заглушка",
            }
        ],
    }


def create_suggestion(
    *,
    revision: FMEARevision,
    component: Component,
    user: User,
    hints: str = "",
    request=None,
) -> LLMSuggestion:
    prompt = build_prompt(revision, component, hints)
    suggestion = LLMSuggestion.objects.create(
        product=revision.product,
        revision=revision,
        component=component,
        prompt=prompt,
        response=build_response(component),
        provider=PROVIDER,
        model_name=MODEL_NAME,
        status=SuggestionStatus.NEW,
        created_by=user,
    )
    log_action(
        user=user,
        action="request",
        entity=suggestion,
        payload={
            "revision_id": revision.pk,
            "component_id": component.pk,
            "provider": PROVIDER,
        },
        request=request,
    )
    return suggestion


@transaction.atomic
def apply_suggestion(suggestion: LLMSuggestion, *, user: User, request=None) -> FMEAItem:
    if suggestion.status != SuggestionStatus.NEW:
        raise ValidationError({"detail": "Предложение уже обработано"})
    if suggestion.revision is None:
        raise ValidationError({"detail": "У предложения нет ревизии"})

    ensure_revision_editable(suggestion.revision, user)
    data = suggestion.response["suggestions"][0]
    item = FMEAItem.objects.create(
        revision=suggestion.revision,
        component=suggestion.component,
        failure_mode=data["failure_mode"],
        failure_cause=data["failure_cause"],
        failure_effect=data["failure_effect"],
        severity=data["severity"],
        occurrence=data["occurrence"],
        detection=data["detection"],
        recommended_action=data.get("recommended_action", ""),
        source_reference=data.get("source_reference", ""),
        source=ItemSource.LLM,
        created_by=user,
    )
    suggestion.status = SuggestionStatus.APPLIED
    suggestion.applied_item = item
    suggestion.save(update_fields=["status", "applied_item"])
    log_action(
        user=user,
        action="apply",
        entity=suggestion,
        payload={
            "item_id": item.pk,
            "revision_id": suggestion.revision_id,
            "source": ItemSource.LLM,
        },
        request=request,
    )
    return item


@transaction.atomic
def reject_suggestion(suggestion: LLMSuggestion, *, user: User, request=None) -> LLMSuggestion:
    if suggestion.status != SuggestionStatus.NEW:
        raise ValidationError({"detail": "Предложение уже обработано"})
    if suggestion.created_by_id != user.pk and not is_quality_or_admin(user):
        raise PermissionDenied("Отклонить предложение может автор, качество или администратор")

    suggestion.status = SuggestionStatus.REJECTED
    suggestion.save(update_fields=["status"])
    log_action(
        user=user,
        action="reject",
        entity=suggestion,
        payload={"suggestion_id": suggestion.pk},
        request=request,
    )
    return suggestion
