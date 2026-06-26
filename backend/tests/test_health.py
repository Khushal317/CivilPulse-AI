from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services.storage import get_image_storage


class FailingStorage:
    def health_check(self) -> None:
        raise AppError(
            code="storage_unavailable",
            message="Image storage is unavailable.",
            status_code=503,
        )


def test_live_health_check(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.headers["X-Request-ID"]


def test_ready_health_check(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_health_check_reports_storage_failure(client: TestClient) -> None:
    app.dependency_overrides[get_image_storage] = lambda: FailingStorage()

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"


def test_v1_api_root(client: TestClient) -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "CivicPulse API", "version": "v1"}


def test_request_id_is_preserved(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "manual-check-123"})

    assert response.headers["X-Request-ID"] == "manual-check-123"


def test_api_metadata_exposes_domain_vocabulary(client: TestClient) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    assert "road_damage" in response.json()["categories"]
    assert "community_verified" in response.json()["statuses"]
