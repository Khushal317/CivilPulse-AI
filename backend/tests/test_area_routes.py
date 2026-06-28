from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import get_area_service
from app.main import app
from app.schemas.areas import (
    AreaCivicGenomeProfile,
    AreaDetail,
    AreaInsightResponse,
    AreaListResponse,
    AreaScoreBreakdown,
    AreaSummary,
)


def area_summary() -> AreaSummary:
    return AreaSummary(
        id=UUID(int=1),
        name="Sector 12",
        slug="civicpulse-city-sector-12",
        city="CivicPulse City",
        rank=1,
        status_label="improving",
        scores=AreaScoreBreakdown(
            overall=70,
            infrastructure=70,
            cleanliness=70,
            safety=70,
            participation=70,
            responsiveness=70,
            environment=70,
        ),
        civic_genome=AreaCivicGenomeProfile(
            civic_health_score=70,
            community_power_score=70,
            confidence_level="medium",
            confidence_reason="This score is based on moderate activity.",
            score_limit_reasons=[],
        ),
        open_issues=2,
        resolved_this_week=1,
        active_missions=0,
        created_at=datetime(2026, 6, 27, tzinfo=UTC),
        updated_at=datetime(2026, 6, 27, tzinfo=UTC),
    )


class FakeAreaService:
    def __init__(self) -> None:
        self.slug: str | None = None

    def list_public(self) -> AreaListResponse:
        return AreaListResponse(items=[area_summary()])

    def get_public_detail(self, slug: str) -> AreaDetail:
        self.slug = slug
        return AreaDetail(
            **area_summary().model_dump(),
            total_issues=5,
            insight=AreaInsightResponse(
                explanation="Sector 12 is improving with useful public civic signals.",
                next_best_actions=["Verify safe public issues."],
                model_used="demo-civic-area-explainer-v1",
            ),
        )


def test_public_area_list_route(client: TestClient) -> None:
    service = FakeAreaService()
    app.dependency_overrides[get_area_service] = lambda: service

    response = client.get("/api/v1/areas")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["name"] == "Sector 12"
    assert item["civic_genome"]["civic_health_score"] == 70
    assert item["open_issues"] == 2
    assert "citizen_contact" not in item


def test_public_area_detail_route(client: TestClient) -> None:
    service = FakeAreaService()
    app.dependency_overrides[get_area_service] = lambda: service

    response = client.get("/api/v1/areas/civicpulse-city-sector-12")

    assert response.status_code == 200
    assert service.slug == "civicpulse-city-sector-12"
    assert response.json()["total_issues"] == 5
    assert response.json()["insight"]["next_best_actions"] == ["Verify safe public issues."]
