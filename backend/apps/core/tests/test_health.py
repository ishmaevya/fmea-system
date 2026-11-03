import pytest


@pytest.mark.django_db
def test_health_returns_ok(client):
    response = client.get("/api/health/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "fmea-backend"
    assert payload["checks"]["database"] == "ok"
    assert payload["checks"]["cache"] == "ok"
