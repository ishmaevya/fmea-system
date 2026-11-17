import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Component, MedicalProduct, ProductStatus, ProductVariant
from apps.fmea.models import AuditLog, FMEARevision


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
def product(engineer):
    return MedicalProduct.objects.create(
        code="HUM-001",
        name="Увлажнитель дыхательных смесей",
        manufacturer="",
        created_by=engineer,
    )


@pytest.mark.django_db
def test_products_require_authentication(api_client):
    response = api_client.get("/api/products/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_product_sets_author_and_audit(api_client, engineer):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/products/",
        {
            "code": "HUM-002",
            "name": "Увлажнитель дыхательных смесей",
            "manufacturer": "",
            "description": "Тестовое изделие",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created_by"] == engineer.pk
    assert payload["status"] == ProductStatus.ACTIVE
    assert payload["created_by_email"] == engineer.email
    assert AuditLog.objects.filter(
        action="create", entity_type="MedicalProduct", entity_id=str(payload["id"])
    ).exists()


@pytest.mark.django_db
def test_duplicate_product_code_rejected(api_client, engineer, product):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/products/",
        {"code": product.code, "name": "Дубль", "manufacturer": ""},
        format="json",
    )

    assert response.status_code == 400
    assert "code" in response.json()


@pytest.mark.django_db
def test_archive_requires_quality_role(api_client, engineer, quality, product):
    api_client.force_authenticate(engineer)
    forbidden = api_client.delete(f"/api/products/{product.pk}/")
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    archived = api_client.delete(f"/api/products/{product.pk}/")
    assert archived.status_code == 204

    product.refresh_from_db()
    assert product.status == ProductStatus.ARCHIVED
    assert MedicalProduct.objects.filter(pk=product.pk).exists()

    again = api_client.delete(f"/api/products/{product.pk}/")
    assert again.status_code == 204


@pytest.mark.django_db
def test_status_change_requires_quality_role(api_client, engineer, quality, product):
    api_client.force_authenticate(engineer)
    forbidden = api_client.patch(
        f"/api/products/{product.pk}/",
        {"status": ProductStatus.ARCHIVED},
        format="json",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(quality)
    allowed = api_client.patch(
        f"/api/products/{product.pk}/",
        {"status": ProductStatus.ARCHIVED},
        format="json",
    )
    assert allowed.status_code == 200
    assert allowed.json()["status"] == ProductStatus.ARCHIVED


@pytest.mark.django_db
def test_nested_variants_and_product_mismatch(api_client, engineer, product):
    api_client.force_authenticate(engineer)

    created = api_client.post(
        f"/api/products/{product.pk}/variants/",
        {"code": "V-01", "name": "Исполнение 1"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["product"] == product.pk

    other = MedicalProduct.objects.create(
        code="HUM-999", name="Другое изделие", manufacturer="", created_by=engineer
    )
    mismatch = api_client.post(
        f"/api/products/{product.pk}/variants/",
        {"product": other.pk, "code": "V-02", "name": "Исполнение 2"},
        format="json",
    )
    assert mismatch.status_code == 400
    assert "product" in mismatch.json()


@pytest.mark.django_db
def test_standalone_variant_requires_product(api_client, engineer):
    api_client.force_authenticate(engineer)

    response = api_client.post(
        "/api/variants/", {"code": "V-01", "name": "Исполнение 1"}, format="json"
    )

    assert response.status_code == 400
    assert "product" in response.json()


@pytest.mark.django_db
def test_variant_with_revision_cannot_be_deleted(api_client, engineer, product):
    variant = ProductVariant.objects.create(product=product, code="V-01", name="Исполнение 1")
    FMEARevision.objects.create(
        product=product, variant=variant, version="1.0", created_by=engineer
    )
    api_client.force_authenticate(engineer)

    response = api_client.delete(f"/api/variants/{variant.pk}/")

    assert response.status_code == 400
    assert ProductVariant.objects.filter(pk=variant.pk).exists()


@pytest.mark.django_db
def test_variant_without_links_is_deleted(api_client, engineer, product):
    variant = ProductVariant.objects.create(product=product, code="V-01", name="Исполнение 1")
    api_client.force_authenticate(engineer)

    response = api_client.delete(f"/api/variants/{variant.pk}/")

    assert response.status_code == 204
    assert not ProductVariant.objects.filter(pk=variant.pk).exists()


@pytest.mark.django_db
def test_nested_components_and_parent_validation(api_client, engineer, product):
    api_client.force_authenticate(engineer)

    parent_response = api_client.post(
        f"/api/products/{product.pk}/components/",
        {"code": "BU", "name": "Блок управления", "criticality": "critical"},
        format="json",
    )
    assert parent_response.status_code == 201
    parent = Component.objects.get(pk=parent_response.json()["id"])

    child_response = api_client.post(
        f"/api/products/{product.pk}/components/",
        {"code": "PANEL", "name": "Панель", "parent": parent.pk},
        format="json",
    )
    assert child_response.status_code == 201

    other = MedicalProduct.objects.create(
        code="HUM-999", name="Другое изделие", manufacturer="", created_by=engineer
    )
    alien_parent = Component.objects.create(product=other, code="X", name="Чужой узел")
    invalid_parent = api_client.post(
        f"/api/products/{product.pk}/components/",
        {"code": "HEATER", "name": "Нагреватель", "parent": alien_parent.pk},
        format="json",
    )
    assert invalid_parent.status_code == 400
    assert "parent" in invalid_parent.json()


@pytest.mark.django_db
def test_component_parent_cycle_rejected(api_client, engineer, product):
    first = Component.objects.create(product=product, code="A", name="Узел A")
    second = Component.objects.create(product=product, code="B", name="Узел B", parent=first)
    api_client.force_authenticate(engineer)

    self_parent = api_client.patch(
        f"/api/components/{first.pk}/", {"parent": first.pk}, format="json"
    )
    assert self_parent.status_code == 400

    cycle = api_client.patch(f"/api/components/{first.pk}/", {"parent": second.pk}, format="json")
    assert cycle.status_code == 400
    assert "parent" in cycle.json()


@pytest.mark.django_db
def test_delete_component_deactivates_it(api_client, engineer, product):
    component = Component.objects.create(product=product, code="BU", name="Блок управления")
    api_client.force_authenticate(engineer)

    response = api_client.delete(f"/api/components/{component.pk}/")

    assert response.status_code == 204
    component.refresh_from_db()
    assert component.is_active is False
    assert Component.objects.filter(pk=component.pk).exists()
