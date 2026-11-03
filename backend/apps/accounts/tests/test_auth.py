import pytest

from apps.accounts.models import User


@pytest.mark.django_db
def test_token_obtain_and_me(client):
    User.objects.create_user(
        email="engineer@example.com",
        password="StrongPass123",
        full_name="Инженер И.И.",
        role=User.Role.ENGINEER,
    )

    response = client.post(
        "/api/auth/token/",
        data={"email": "engineer@example.com", "password": "StrongPass123"},
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert "access" in payload
    assert "refresh" in payload
    assert payload["user"]["email"] == "engineer@example.com"
    assert payload["user"]["role"] == "engineer"

    me_response = client.get(
        "/api/auth/me/",
        HTTP_AUTHORIZATION=f"Bearer {payload['access']}",
    )
    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Инженер И.И."


@pytest.mark.django_db
def test_me_requires_authentication(client):
    response = client.get("/api/auth/me/")

    assert response.status_code == 401
