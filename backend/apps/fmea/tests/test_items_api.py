import pytest

from apps.catalog.models import Component, MedicalProduct
from apps.fmea.models import AuditLog, FMEAItem, RevisionStatus


@pytest.mark.django_db
def test_items_require_authentication(api_client, revision):
    response = api_client.get(f"/api/revisions/{revision.pk}/items/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_item_computes_rpn_and_audits(api_client, engineer, revision, component):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/items/",
        {
            "component": component.pk,
            "failure_mode": "Перегрев нагревателя",
            "failure_cause": "Отказ термостата",
            "failure_effect": "Риск ожога",
            "severity": 9,
            "occurrence": 4,
            "detection": 3,
            "recommended_action": "Проверка термостата",
            "source_reference": "Анализ функциональных отказов",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["rpn"] == 108
    assert payload["action_priority"] == "medium"
    assert payload["created_by"] == engineer.pk
    assert payload["component_code"] == component.code
    assert AuditLog.objects.filter(
        action="create", entity_type="FMEAItem", entity_id=str(payload["id"])
    ).exists()


@pytest.mark.django_db
def test_create_item_validates_scores_and_component(api_client, engineer, revision, component):
    api_client.force_authenticate(engineer)
    payload = {
        "component": component.pk,
        "failure_mode": "Перегрев",
        "failure_cause": "Причина",
        "failure_effect": "Последствие",
        "severity": 11,
        "occurrence": 4,
        "detection": 3,
    }

    invalid_score = api_client.post(f"/api/revisions/{revision.pk}/items/", payload, format="json")
    assert invalid_score.status_code == 400
    assert "severity" in invalid_score.json()

    other = MedicalProduct.objects.create(
        code="HUM-999", name="Другое изделие", manufacturer="", created_by=engineer
    )
    alien = Component.objects.create(product=other, code="X", name="Чужой компонент")
    payload.update({"severity": 5, "component": alien.pk})
    alien_component = api_client.post(
        f"/api/revisions/{revision.pk}/items/", payload, format="json"
    )
    assert alien_component.status_code == 400
    assert "component" in alien_component.json()


@pytest.mark.django_db
def test_items_filter_and_ordering(api_client, engineer, revision, component, item_factory):
    item_factory(revision, component, failure_mode="Низкий", severity=3, occurrence=3, detection=3)
    critical = item_factory(
        revision, component, failure_mode="Критический", severity=10, occurrence=5, detection=5
    )
    api_client.force_authenticate(engineer)

    response = api_client.get(
        f"/api/revisions/{revision.pk}/items/",
        {"action_priority": "critical", "ordering": "-rpn"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert [row["id"] for row in results] == [critical.pk]
    assert results[0]["rpn"] == 250


@pytest.mark.django_db
def test_update_item_recomputes_rpn(api_client, engineer, revision, component, item_factory):
    item = item_factory(revision, component)
    api_client.force_authenticate(engineer)

    response = api_client.patch(f"/api/items/{item.pk}/", {"severity": 10}, format="json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["rpn"] == 120
    assert payload["action_priority"] == "medium"
    assert AuditLog.objects.filter(action="update", entity_id=str(item.pk)).exists()


@pytest.mark.django_db
def test_delete_item_in_draft(api_client, engineer, revision, component, item_factory):
    item = item_factory(revision, component)
    api_client.force_authenticate(engineer)

    response = api_client.delete(f"/api/items/{item.pk}/")

    assert response.status_code == 204
    assert not FMEAItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_review_edits_require_quality(
    api_client, engineer, quality, revision, component, item_factory
):
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])
    item = item_factory(revision, component)

    api_client.force_authenticate(engineer)
    forbidden = api_client.patch(f"/api/items/{item.pk}/", {"severity": 10}, format="json")
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    allowed = api_client.patch(f"/api/items/{item.pk}/", {"severity": 10}, format="json")
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_approved_revision_is_read_only(api_client, quality, revision, component, item_factory):
    revision.status = RevisionStatus.APPROVED
    revision.save(update_fields=["status"])
    item = item_factory(revision, component)
    api_client.force_authenticate(quality)

    assert (
        api_client.patch(f"/api/items/{item.pk}/", {"severity": 10}, format="json").status_code
        == 403
    )
    assert api_client.delete(f"/api/items/{item.pk}/").status_code == 403
    assert (
        api_client.post(
            f"/api/revisions/{revision.pk}/items/",
            {
                "component": component.pk,
                "failure_mode": "X",
                "failure_cause": "Y",
                "failure_effect": "Z",
                "severity": 5,
                "occurrence": 5,
                "detection": 5,
            },
            format="json",
        ).status_code
        == 403
    )
    assert (
        api_client.post(
            f"/api/revisions/{revision.pk}/items/bulk/", {"items": []}, format="json"
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_bulk_upsert_creates_updates_and_deletes(
    api_client, engineer, revision, component, item_factory
):
    updated = item_factory(revision, component)
    deleted = item_factory(revision, component, failure_mode="Удаляемый")
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/items/bulk/",
        {
            "items": [
                {
                    "id": updated.pk,
                    "component": component.pk,
                    "failure_mode": "Обновлённый",
                    "failure_cause": "Причина",
                    "failure_effect": "Последствие",
                    "severity": 10,
                    "occurrence": 5,
                    "detection": 5,
                },
                {
                    "component": component.pk,
                    "failure_mode": "Новый",
                    "failure_cause": "Причина",
                    "failure_effect": "Последствие",
                    "severity": 6,
                    "occurrence": 6,
                    "detection": 6,
                },
            ],
            "deleted_ids": [deleted.pk],
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 1
    assert payload["updated"] == 1
    assert payload["deleted"] == 1

    updated.refresh_from_db()
    assert updated.failure_mode == "Обновлённый"
    assert updated.rpn == 250
    assert not FMEAItem.objects.filter(pk=deleted.pk).exists()
    assert revision.items.count() == 2
    assert AuditLog.objects.filter(action="bulk_update", entity_id=str(revision.pk)).exists()


@pytest.mark.django_db
def test_bulk_is_atomic(api_client, engineer, revision, component, item_factory):
    existing = item_factory(revision, component)
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/items/bulk/",
        {
            "items": [
                {
                    "id": existing.pk,
                    "component": component.pk,
                    "failure_mode": existing.failure_mode,
                    "failure_cause": existing.failure_cause,
                    "failure_effect": existing.failure_effect,
                    "severity": 15,
                    "occurrence": 5,
                    "detection": 5,
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 400
    existing.refresh_from_db()
    assert existing.severity == 9
    assert revision.items.count() == 1


@pytest.mark.django_db
def test_bulk_rejects_foreign_and_missing_ids(
    api_client, engineer, revision, component, item_factory
):
    item = item_factory(revision, component)
    api_client.force_authenticate(engineer)

    missing = api_client.post(
        f"/api/revisions/{revision.pk}/items/bulk/",
        {"items": [], "deleted_ids": [item.pk + 1000]},
        format="json",
    )
    assert missing.status_code == 400

    overlap = api_client.post(
        f"/api/revisions/{revision.pk}/items/bulk/",
        {
            "items": [
                {
                    "id": item.pk,
                    "component": component.pk,
                    "failure_mode": "X",
                    "failure_cause": "Y",
                    "failure_effect": "Z",
                    "severity": 5,
                    "occurrence": 5,
                    "detection": 5,
                }
            ],
            "deleted_ids": [item.pk],
        },
        format="json",
    )
    assert overlap.status_code == 400


@pytest.mark.django_db
def test_graph_returns_nodes_and_edges(api_client, engineer, revision, component, item_factory):
    first = item_factory(revision, component, failure_mode="Первый")
    second = item_factory(revision, component, failure_mode="Второй")
    revision.dependencies.create(source_item=second, target_item=first, relation_type="causes")
    api_client.force_authenticate(engineer)

    response = api_client.get(f"/api/revisions/{revision.pk}/graph/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["revision"] == revision.pk
    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
    node = payload["nodes"][0]
    assert {"component_code", "failure_mode", "rpn", "action_priority"} <= set(node)
    edge = payload["edges"][0]
    assert edge["source"] == second.pk
    assert edge["target"] == first.pk
