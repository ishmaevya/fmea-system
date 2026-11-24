import pytest

from apps.accounts.models import User
from apps.catalog.models import Component, MedicalProduct
from apps.fmea.models import (
    AuditLog,
    FMEAItem,
    ItemSource,
    LLMSuggestion,
    RevisionStatus,
    SuggestionStatus,
)


def request_suggestion(api_client, user, revision, component, **extra):
    api_client.force_authenticate(user)
    payload = {"revision": revision.pk, "component": component.pk, **extra}
    return api_client.post("/api/suggestions/", payload, format="json")


@pytest.mark.django_db
def test_suggestions_require_authentication(api_client, revision):
    assert api_client.get("/api/suggestions/").status_code == 401


@pytest.mark.django_db
def test_create_stub_suggestion(api_client, engineer, revision, component):
    response = request_suggestion(
        api_client, engineer, revision, component, hints="Проверить нагрев"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "stub"
    assert data["model_name"] == "rule-based-demo-v1"
    assert data["status"] == SuggestionStatus.NEW
    assert data["component_code"] == component.code
    assert data["created_by_email"] == "engineer@example.com"
    assert "Проверить нагрев" in data["prompt"]
    assert "не реальная языковая модель" in data["response"]["disclaimer"]
    assert len(data["response"]["suggestions"]) == 1

    suggestion = LLMSuggestion.objects.get(pk=data["id"])
    assert suggestion.revision_id == revision.pk
    assert suggestion.product_id == revision.product_id
    assert suggestion.response["suggestions"][0]["severity"] in range(5, 11)


@pytest.mark.django_db
def test_suggestion_requires_component_of_revision_product(
    api_client, engineer, revision, product, component
):
    other_product = MedicalProduct.objects.create(
        code="HUM-002", name="Другое изделие", manufacturer="", created_by=engineer
    )
    other_component = Component.objects.create(
        product=other_product, code="OTHER", name="Другой компонент"
    )

    response = request_suggestion(api_client, engineer, revision, other_component)
    assert response.status_code == 400
    assert "component" in response.json()


@pytest.mark.django_db
def test_apply_suggestion_creates_llm_item_and_audits(api_client, engineer, revision, component):
    created = request_suggestion(api_client, engineer, revision, component)
    assert created.status_code == 201
    suggestion_id = created.json()["id"]

    api_client.force_authenticate(engineer)
    response = api_client.post(f"/api/suggestions/{suggestion_id}/apply/")

    assert response.status_code == 200
    data = response.json()
    assert data["source"] == ItemSource.LLM
    assert data["rpn"] == data["severity"] * data["occurrence"] * data["detection"]
    assert data["revision"] == revision.pk

    suggestion = LLMSuggestion.objects.get(pk=suggestion_id)
    assert suggestion.status == SuggestionStatus.APPLIED
    assert suggestion.applied_item_id == data["id"]
    assert FMEAItem.objects.filter(pk=data["id"]).count() == 1
    assert AuditLog.objects.filter(
        action="apply", entity_type="LLMSuggestion", entity_id=str(suggestion_id)
    ).exists()


@pytest.mark.django_db
def test_apply_respects_revision_permissions(api_client, engineer, quality, revision, component):
    created = request_suggestion(api_client, engineer, revision, component)
    suggestion_id = created.json()["id"]

    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])
    api_client.force_authenticate(engineer)
    denied = api_client.post(f"/api/suggestions/{suggestion_id}/apply/")
    assert denied.status_code == 403

    api_client.force_authenticate(quality)
    allowed = api_client.post(f"/api/suggestions/{suggestion_id}/apply/")
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_applied_suggestion_cannot_be_applied_twice(api_client, engineer, revision, component):
    created = request_suggestion(api_client, engineer, revision, component)
    suggestion_id = created.json()["id"]

    api_client.force_authenticate(engineer)
    assert api_client.post(f"/api/suggestions/{suggestion_id}/apply/").status_code == 200
    repeated = api_client.post(f"/api/suggestions/{suggestion_id}/apply/")
    assert repeated.status_code == 400


@pytest.mark.django_db
def test_approved_revision_rejects_apply(api_client, engineer, revision, component):
    created = request_suggestion(api_client, engineer, revision, component)
    suggestion_id = created.json()["id"]

    revision.status = RevisionStatus.APPROVED
    revision.save(update_fields=["status"])
    api_client.force_authenticate(engineer)
    response = api_client.post(f"/api/suggestions/{suggestion_id}/apply/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_reject_suggestion_permissions(api_client, engineer, quality, revision, component):
    created = request_suggestion(api_client, engineer, revision, component)
    suggestion_id = created.json()["id"]

    other = User.objects.create_user(
        email="other@example.com",
        password="Pass12345!",
        role=User.Role.ENGINEER,
        full_name="Другой инженер",
        position="Инженер-конструктор",
    )
    api_client.force_authenticate(other)
    denied = api_client.post(f"/api/suggestions/{suggestion_id}/reject/")
    assert denied.status_code == 403

    api_client.force_authenticate(quality)
    allowed = api_client.post(f"/api/suggestions/{suggestion_id}/reject/")
    assert allowed.status_code == 200
    assert allowed.json()["status"] == SuggestionStatus.REJECTED

    suggestion = LLMSuggestion.objects.get(pk=suggestion_id)
    assert suggestion.status == SuggestionStatus.REJECTED
    assert suggestion.applied_item_id is None


@pytest.mark.django_db
def test_list_filters_suggestions(api_client, engineer, revision, component):
    first = request_suggestion(api_client, engineer, revision, component)
    assert first.status_code == 201
    second = request_suggestion(api_client, engineer, revision, component)
    assert second.status_code == 201

    api_client.force_authenticate(engineer)
    assert api_client.get(f"/api/suggestions/?revision={revision.pk}").json()["count"] == 2

    api_client.post(f"/api/suggestions/{second.json()['id']}/reject/")
    rejected = api_client.get(
        f"/api/suggestions/?revision={revision.pk}&status={SuggestionStatus.REJECTED}"
    )
    assert rejected.json()["count"] == 1
    assert rejected.json()["results"][0]["id"] == second.json()["id"]
