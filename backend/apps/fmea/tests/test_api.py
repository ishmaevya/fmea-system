import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Component, MedicalProduct, ProductVariant
from apps.fmea.models import (
    AuditLog,
    DependencyType,
    FMEAItem,
    FMEARevision,
    ItemStatus,
    RevisionStatus,
    RiskDependency,
)


@pytest.fixture
def api_client():
    return APIClient()


def make_user(email: str, role: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Pass12345!",
        role=role,
        full_name=email,
        position="Тестовая должность",
    )


@pytest.fixture
def engineer(db):
    return make_user("engineer@example.com", User.Role.ENGINEER)


@pytest.fixture
def quality(db):
    return make_user("quality@example.com", User.Role.QUALITY)


@pytest.fixture
def admin_user(db):
    return make_user("admin@example.com", User.Role.ADMIN)


@pytest.fixture
def product(engineer):
    return MedicalProduct.objects.create(
        code="HUM-001",
        name="Увлажнитель дыхательных смесей",
        manufacturer="",
        created_by=engineer,
    )


@pytest.fixture
def variant(product):
    return ProductVariant.objects.create(product=product, code="V-01", name="Исполнение 1")


@pytest.fixture
def component(product):
    return Component.objects.create(product=product, code="HEATER", name="Нагреватель воды")


@pytest.fixture
def revision(product, variant, engineer):
    return FMEARevision.objects.create(
        product=product, variant=variant, version="1.0", created_by=engineer
    )


def make_item(revision, component, user, mode="Перегрев нагревателя"):
    return FMEAItem.objects.create(
        revision=revision,
        component=component,
        failure_mode=mode,
        failure_cause="Отказ термостата",
        failure_effect="Риск ожога",
        severity=9,
        occurrence=4,
        detection=3,
        created_by=user,
    )


@pytest.mark.django_db
def test_revisions_require_authentication(api_client):
    response = api_client.get("/api/revisions/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_revision_auto_version_and_audit(api_client, engineer, product, variant):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/revisions/",
        {"product": product.pk, "variant": variant.pk, "change_reason": "Первичная ревизия"},
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["version"] == "1.0"
    assert payload["status"] == RevisionStatus.DRAFT
    assert payload["created_by"] == engineer.pk
    assert payload["product_code"] == product.code
    assert payload["variant_code"] == variant.code
    assert AuditLog.objects.filter(
        action="create", entity_type="FMEARevision", entity_id=str(payload["id"])
    ).exists()


@pytest.mark.django_db
def test_duplicate_revision_version_rejected(api_client, engineer, product, variant, revision):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/revisions/",
        {"product": product.pk, "variant": variant.pk, "version": revision.version},
        format="json",
    )

    assert response.status_code == 400
    assert "version" in response.json()


@pytest.mark.django_db
def test_revision_variant_must_match_product(api_client, engineer, product):
    other = MedicalProduct.objects.create(
        code="HUM-999", name="Другое изделие", manufacturer="", created_by=engineer
    )
    alien_variant = ProductVariant.objects.create(product=other, code="V-01", name="Исполнение 1")
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/revisions/",
        {"product": product.pk, "variant": alien_variant.pk},
        format="json",
    )

    assert response.status_code == 400
    assert "variant" in response.json()


@pytest.mark.django_db
def test_submit_empty_revision_rejected(api_client, engineer, revision):
    api_client.force_authenticate(engineer)

    response = api_client.post(f"/api/revisions/{revision.pk}/submit/")

    assert response.status_code == 400
    revision.refresh_from_db()
    assert revision.status == RevisionStatus.DRAFT


@pytest.mark.django_db
def test_submit_and_invalid_transition(api_client, engineer, revision, component):
    make_item(revision, component, engineer)
    api_client.force_authenticate(engineer)

    submitted = api_client.post(f"/api/revisions/{revision.pk}/submit/")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == RevisionStatus.REVIEW

    again = api_client.post(f"/api/revisions/{revision.pk}/submit/")
    assert again.status_code == 400


@pytest.mark.django_db
def test_approve_permissions_and_state(api_client, engineer, quality, revision, component):
    make_item(revision, component, engineer)
    api_client.force_authenticate(engineer)
    api_client.post(f"/api/revisions/{revision.pk}/submit/")

    api_client.force_authenticate(engineer)
    forbidden = api_client.post(f"/api/revisions/{revision.pk}/approve/")
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    approved = api_client.post(f"/api/revisions/{revision.pk}/approve/")
    assert approved.status_code == 200
    payload = approved.json()
    assert payload["status"] == RevisionStatus.APPROVED
    assert payload["approved_by"] == quality.pk
    assert payload["approved_by_email"] == quality.email
    assert payload["approved_at"] is not None
    assert AuditLog.objects.filter(action="approve", entity_id=str(revision.pk)).exists()


@pytest.mark.django_db
def test_approve_draft_rejected(api_client, quality, revision):
    api_client.force_authenticate(quality)

    response = api_client.post(f"/api/revisions/{revision.pk}/approve/")

    assert response.status_code == 400


@pytest.mark.django_db
def test_reject_requires_quality_and_reason(api_client, engineer, quality, revision):
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])

    api_client.force_authenticate(engineer)
    forbidden = api_client.post(
        f"/api/revisions/{revision.pk}/reject/", {"reason": "Нужно доработать"}, format="json"
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    no_reason = api_client.post(f"/api/revisions/{revision.pk}/reject/", {}, format="json")
    assert no_reason.status_code == 400

    rejected = api_client.post(
        f"/api/revisions/{revision.pk}/reject/", {"reason": "Нужно доработать"}, format="json"
    )
    assert rejected.status_code == 200
    payload = rejected.json()
    assert payload["status"] == RevisionStatus.DRAFT
    assert payload["change_reason"] == "Нужно доработать"
    assert AuditLog.objects.filter(action="reject", entity_id=str(revision.pk)).exists()


@pytest.mark.django_db
def test_archive_permissions(api_client, engineer, quality, admin_user, revision):
    api_client.force_authenticate(quality)
    forbidden = api_client.post(f"/api/revisions/{revision.pk}/archive/")
    assert forbidden.status_code == 403

    api_client.force_authenticate(admin_user)
    archived = api_client.post(f"/api/revisions/{revision.pk}/archive/")
    assert archived.status_code == 200
    assert archived.json()["status"] == RevisionStatus.ARCHIVED


@pytest.mark.django_db
def test_archive_review_rejected(api_client, admin_user, revision):
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])
    api_client.force_authenticate(admin_user)

    response = api_client.post(f"/api/revisions/{revision.pk}/archive/")

    assert response.status_code == 400


@pytest.mark.django_db
def test_clone_copies_items_and_dependencies(api_client, engineer, revision, component):
    first = make_item(revision, component, engineer, mode="Перегрев")
    second = make_item(revision, component, engineer, mode="Отказ термостата")
    RiskDependency.objects.create(
        revision=revision,
        source_item=second,
        target_item=first,
        relation_type=DependencyType.CAUSES,
    )
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/clone/", {"change_reason": "Новая версия"}, format="json"
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] != revision.pk
    assert payload["version"] == "1.1"
    assert payload["based_on"] == revision.pk
    assert payload["status"] == RevisionStatus.DRAFT
    assert payload["items_count"] == 2
    assert payload["dependencies_count"] == 1
    assert payload["change_reason"] == "Новая версия"

    cloned = FMEARevision.objects.get(pk=payload["id"])
    assert set(cloned.items.values_list("status", flat=True)) == {ItemStatus.OPEN}
    assert revision.items.count() == 2
    assert AuditLog.objects.filter(action="clone", entity_id=str(cloned.pk)).exists()


@pytest.mark.django_db
def test_clone_archived_revision_rejected(api_client, engineer, revision):
    revision.status = RevisionStatus.ARCHIVED
    revision.save(update_fields=["status"])
    api_client.force_authenticate(engineer)

    response = api_client.post(f"/api/revisions/{revision.pk}/clone/", {}, format="json")

    assert response.status_code == 400
