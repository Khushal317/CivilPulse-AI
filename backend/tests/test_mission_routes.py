from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_mission_service
from app.domain.enums import IssueCategory
from app.domain.missions import MissionStatus, MissionType
from app.main import app
from app.schemas.missions import (
    MissionAreaSummary,
    MissionDetail,
    MissionListResponse,
    MissionSummary,
)


def mission_area() -> MissionAreaSummary:
    return MissionAreaSummary(
        id=UUID(int=1),
        name="Sector 12",
        slug="civicpulse-city-sector-12",
        city="CivicPulse City",
    )


def mission_summary() -> MissionSummary:
    now = datetime(2026, 6, 27, tzinfo=UTC)
    return MissionSummary(
        id=UUID(int=2),
        title="Verify repaired streetlights",
        mission_type=MissionType.VERIFICATION,
        status=MissionStatus.ACTIVE,
        area=mission_area(),
        goal_description="Ask nearby residents to confirm the streetlights are working.",
        target_count=5,
        progress_count=2,
        category=IssueCategory.STREETLIGHT,
        reward={"points": 20, "score_key": "participation"},
        ai_reason="Several residents reported lighting issues in this area.",
        expires_at=now + timedelta(days=7),
        published_at=now,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )


class FakeMissionService:
    def __init__(self) -> None:
        self.mission_id: UUID | None = None

    def list_public(self) -> MissionListResponse:
        return MissionListResponse(items=[mission_summary()])

    def get_public_detail(self, mission_id: UUID) -> MissionDetail:
        self.mission_id = mission_id
        return MissionDetail(
            **mission_summary().model_dump(),
            linked_issue_ids=[UUID(int=10)],
        )


def test_public_mission_list_route(client: TestClient) -> None:
    service = FakeMissionService()
    app.dependency_overrides[get_mission_service] = lambda: service

    response = client.get("/api/v1/missions")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["title"] == "Verify repaired streetlights"
    assert item["area"]["name"] == "Sector 12"
    assert item["progress_count"] == 2


def test_public_mission_detail_route(client: TestClient) -> None:
    service = FakeMissionService()
    app.dependency_overrides[get_mission_service] = lambda: service

    response = client.get("/api/v1/missions/00000000-0000-0000-0000-000000000002")

    assert response.status_code == 200
    assert service.mission_id == UUID(int=2)
    assert response.json()["linked_issue_ids"] == ["00000000-0000-0000-0000-00000000000a"]
