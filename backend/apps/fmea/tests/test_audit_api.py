from datetime import timedelta

import pytest
from django.utils import timezone

from apps.fmea.audit import log_action


@pytest.fixture
def audit_events(engineer, quality):
    now = timezone.now()
    first = log_action(
        user=engineer,
        action="create",
        entity="FMEARevision",
        payload={"revision_id": 1},
    )
    second = log_action(
        user=quality,
        action="approve",
        entity="FMEARevision",
        payload={"revision_id": 1, "password": "secret"},
    )
    return first, second, now


@pytest.mark.django_db
def test_audit_requires_admin(api_client, audit_events, engineer, quality, admin_user):
    assert api_client.get("/api/audit/").status_code == 401

    api_client.force_authenticate(engineer)
    assert api_client.get("/api/audit/").status_code == 403

    api_client.force_authenticate(quality)
    assert api_client.get("/api/audit/").status_code == 403

    api_client.force_authenticate(admin_user)
    response = api_client.get("/api/audit/")
    assert response.status_code == 200
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_audit_list_fields_and_order(api_client, audit_events, admin_user, engineer):
    _, second, _ = audit_events
    api_client.force_authenticate(admin_user)

    response = api_client.get("/api/audit/")
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["id"] == second.pk
    assert results[0]["action"] == "approve"
    assert results[0]["user_email"] == "quality@example.com"
    assert results[0]["entity_type"] == "FMEARevision"
    assert results[0]["created_at"]

    by_user = api_client.get(f"/api/audit/?user={engineer.pk}")
    assert by_user.json()["count"] == 1
    assert by_user.json()["results"][0]["user"] == engineer.pk

    by_action = api_client.get("/api/audit/?action=approve")
    assert by_action.json()["count"] == 1

    by_entity = api_client.get("/api/audit/?entity_type=FMEARevision")
    assert by_entity.json()["count"] == 2

    by_date_from = api_client.get(
        f"/api/audit/?date_from={(timezone.now() + timedelta(days=1)).date().isoformat()}"
    )
    assert by_date_from.json()["count"] == 0

    by_date_to = api_client.get(
        f"/api/audit/?date_to={(timezone.now() + timedelta(days=1)).date().isoformat()}"
    )
    assert by_date_to.json()["count"] == 2


@pytest.mark.django_db
def test_audit_payload_is_sanitized(api_client, audit_events, admin_user):
    log_action(
        user=admin_user,
        action="export",
        entity="FMEARevision",
        payload={"token": "abc", "nested": {"password": "secret", "safe": 1}},
    )
    api_client.force_authenticate(admin_user)

    response = api_client.get("/api/audit/?action=export")
    assert response.status_code == 200
    payload = response.json()["results"][0]["payload"]
    assert payload["token"] == "***"
    assert payload["nested"]["password"] == "***"
    assert payload["nested"]["safe"] == 1


@pytest.mark.django_db
def test_audit_retrieve_and_search(api_client, audit_events, admin_user):
    _, second, _ = audit_events
    api_client.force_authenticate(admin_user)

    detail = api_client.get(f"/api/audit/{second.pk}/")
    assert detail.status_code == 200
    assert detail.json()["action"] == "approve"

    found = api_client.get("/api/audit/?search=approve")
    assert found.json()["count"] == 1
    assert found.json()["results"][0]["id"] == second.pk
