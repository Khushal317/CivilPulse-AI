from fastapi.testclient import TestClient


def test_live_health_check(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.headers["X-Request-ID"]


def test_ready_health_check(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


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
