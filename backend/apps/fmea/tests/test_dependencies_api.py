import pytest

from apps.fmea.models import FMEARevision, RevisionStatus


@pytest.mark.django_db
def test_create_dependency(api_client, engineer, revision, component, item_factory):
    source = item_factory(revision, component, failure_mode="Источник")
    target = item_factory(revision, component, failure_mode="Цель")
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/",
        {
            "source_item": source.pk,
            "target_item": target.pk,
            "relation_type": "causes",
            "description": "Вызывает отказ",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["revision"] == revision.pk
    assert payload["source_item"] == source.pk
    assert payload["target_item"] == target.pk
    assert payload["source_mode"] == "Источник"
    assert payload["relation_type_display"] == "Вызывает"


@pytest.mark.django_db
def test_dependency_validation(api_client, engineer, revision, component, item_factory):
    source = item_factory(revision, component, failure_mode="Источник")
    item_factory(revision, component, failure_mode="Цель")
    api_client.force_authenticate(engineer)

    self_link = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/",
        {"source_item": source.pk, "target_item": source.pk, "relation_type": "causes"},
        format="json",
    )
    assert self_link.status_code == 400
    assert "target_item" in self_link.json()

    other_revision = FMEARevision.objects.create(
        product=revision.product, variant=revision.variant, version="1.1", created_by=engineer
    )
    foreign = item_factory(other_revision, component, failure_mode="Чужой")
    cross = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/",
        {"source_item": source.pk, "target_item": foreign.pk, "relation_type": "causes"},
        format="json",
    )
    assert cross.status_code == 400
    assert "target_item" in cross.json()


@pytest.mark.django_db
def test_duplicate_dependency_rejected(
    api_client, engineer, revision, component, item_factory
):
    source = item_factory(revision, component, failure_mode="Источник")
    target = item_factory(revision, component, failure_mode="Цель")
    revision.dependencies.create(
        source_item=source, target_item=target, relation_type="causes"
    )
    api_client.force_authenticate(engineer)

    response = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/",
        {"source_item": source.pk, "target_item": target.pk, "relation_type": "causes"},
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_dependency_permissions(
    api_client, engineer, quality, revision, component, item_factory
):
    source = item_factory(revision, component, failure_mode="Источник")
    target = item_factory(revision, component, failure_mode="Цель")
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])
    payload = {
        "source_item": source.pk,
        "target_item": target.pk,
        "relation_type": "affects",
    }

    api_client.force_authenticate(engineer)
    forbidden = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/", payload, format="json"
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    allowed = api_client.post(
        f"/api/revisions/{revision.pk}/dependencies/", payload, format="json"
    )
    assert allowed.status_code == 201


@pytest.mark.django_db
def test_dependency_delete_rules(
    api_client, engineer, quality, revision, component, item_factory
):
    source = item_factory(revision, component, failure_mode="Источник")
    target = item_factory(revision, component, failure_mode="Цель")
    dependency = revision.dependencies.create(
        source_item=source, target_item=target, relation_type="mitigates"
    )
    api_client.force_authenticate(engineer)

    deleted = api_client.delete(f"/api/dependencies/{dependency.pk}/")
    assert deleted.status_code == 204

    second = revision.dependencies.create(
        source_item=source, target_item=target, relation_type="causes"
    )
    revision.status = RevisionStatus.APPROVED
    revision.save(update_fields=["status"])
    api_client.force_authenticate(quality)
    forbidden = api_client.delete(f"/api/dependencies/{second.pk}/")
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_dependencies_list_nested(
    api_client, engineer, revision, component, item_factory
):
    source = item_factory(revision, component, failure_mode="Источник")
    target = item_factory(revision, component, failure_mode="Цель")
    revision.dependencies.create(
        source_item=source, target_item=target, relation_type="causes"
    )
    api_client.force_authenticate(engineer)

    response = api_client.get(f"/api/revisions/{revision.pk}/dependencies/")

    assert response.status_code == 200
    assert response.json()["count"] == 1
