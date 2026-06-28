from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.areas import AreaScoreKey
from app.domain.enums import IssueCategory
from app.domain.missions import MissionType
from app.models.area import Area
from app.schemas.missions import ManualMissionDraft
from app.services.mission_refinement import (
    DemoCivicMissionRefiner,
    GeminiCivicMissionRefiner,
    MissionRefinementService,
    SafeFallbackMissionRefiner,
)


def draft() -> ManualMissionDraft:
    return ManualMissionDraft(
        title="Road damage near DMART",
        area_id=UUID(int=1),
        mission_type=MissionType.VERIFICATION,
        goal_description="Ask residents to safely confirm visible road damage.",
        target_count=3,
        category=IssueCategory.ROAD_DAMAGE,
        reward_points=20,
        reward_score_key=AreaScoreKey.PARTICIPATION,
        ai_reason="This mission gathers safe public confirmation before follow-up.",
        linked_issue_ids=[],
        expires_in_days=7,
    )


class FakeGeminiResponse:
    def __init__(self, *, parsed: object | None = None, text: str | None = None) -> None:
        self.parsed = parsed
        self.text = text


class FakeModels:
    def __init__(self, response: FakeGeminiResponse | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> FakeGeminiResponse:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeGenAIClient:
    next_response: FakeGeminiResponse | Exception
    latest_models: FakeModels | None = None

    def __init__(self, **_kwargs: Any) -> None:
        self.models = FakeModels(self.next_response)
        FakeGenAIClient.latest_models = self.models


class FakeMissionRepository:
    def __init__(self) -> None:
        self.area = Area(id=UUID(int=1), name="Sector 12", slug="sector-12", city="Test City")

    def get_area(self, area_id: UUID) -> Area | None:
        if area_id == self.area.id:
            return self.area
        return None


class RaisingRefiner:
    model_name = "raising-refiner"

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        raise TimeoutError("provider unavailable")


@pytest.fixture(autouse=True)
def fake_gemini_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.mission_refinement.genai.Client", FakeGenAIClient)


def settings() -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-refiner-test",
    )


def test_demo_mission_refiner_keeps_manual_draft_safe_and_measurable() -> None:
    refined = DemoCivicMissionRefiner().refine(draft())

    assert refined.title.startswith("Verify ")
    assert refined.area_id == UUID(int=1)
    assert "safe public observation" in refined.goal_description


def test_gemini_mission_refiner_parses_valid_json_and_preserves_admin_fields() -> None:
    raw = draft().model_copy(
        update={
            "title": "Coordinate safe road damage verification near DMART",
            "area_id": UUID(int=999),
            "reward_points": 99,
            "linked_issue_ids": [UUID(int=999)],
        },
    )
    FakeGenAIClient.next_response = FakeGeminiResponse(text=raw.model_dump_json())

    refined = GeminiCivicMissionRefiner(settings()).refine(draft())

    assert refined.title == "Coordinate safe road damage verification near DMART"
    assert refined.area_id == UUID(int=1)
    assert refined.reward_points == 20
    assert refined.linked_issue_ids == []
    assert FakeGenAIClient.latest_models is not None


def test_safe_refiner_falls_back_when_provider_fails() -> None:
    refined = SafeFallbackMissionRefiner(
        RaisingRefiner(),
        DemoCivicMissionRefiner(),
    ).refine(draft())

    assert refined.title.startswith("Verify ")


def test_refinement_service_rejects_unknown_area() -> None:
    service = MissionRefinementService(
        repository=FakeMissionRepository(),
        refiner=DemoCivicMissionRefiner(),
    )

    with pytest.raises(AppError) as caught:
        service.refine(draft().model_copy(update={"area_id": UUID(int=999)}))

    assert caught.value.code == "mission_area_not_found"
