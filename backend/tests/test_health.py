from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_health_check() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_health_check() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_v1_api_root() -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "CivicPulse API", "version": "v1"}

