import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.catalog.models import Component, MedicalProduct, ProductVariant
from apps.fmea.models import FMEAItem, FMEARevision


def make_user(email: str, role: str) -> User:
    return User.objects.create_user(
        email=email,
        password="Pass12345!",
        role=role,
        full_name=email,
        position="Тестовая должность",
    )


@pytest.fixture
def api_client():
    return APIClient()


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


@pytest.fixture
def item_factory(engineer):
    def factory(revision, component, **kwargs):
        data = {
            "failure_mode": "Перегрев нагревателя",
            "failure_cause": "Отказ термостата",
            "failure_effect": "Риск ожога",
            "severity": 9,
            "occurrence": 4,
            "detection": 3,
            "created_by": engineer,
        }
        data.update(kwargs)
        return FMEAItem.objects.create(revision=revision, component=component, **data)

    return factory
