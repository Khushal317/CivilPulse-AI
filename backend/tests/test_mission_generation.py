from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory
from app.domain.missions import MissionStatus, MissionType
from app.models.area import Area
from app.models.mission import Mission
from app.repositories.missions import MissionAreaContext, MissionContext, MissionIssueContext
from app.schemas.missions import GeneratedMissionCandidate, MissionGenerationPayload
from app.services.mission_generation import (
    DemoCivicMissionGenerator,
    GeminiCivicMissionGenerator,
    MissionGenerationService,
    SafeFallbackMissionGenerator,
    mission_generation_prompt,
)

AREA_ID = UUID(int=1)
ISSUE_ID = UUID(int=2)


def mission_context() -> MissionContext:
    return MissionContext(
        areas=[
            MissionAreaContext(
                id=AREA_ID,
                name="Sector 12",
                slug="civicpulse-city-sector-12",
                city="CivicPulse City",
                overall_score=58,
                infrastructure_score=50,
                cleanliness_score=62,
                safety_score=60,
                participation_score=55,
                responsiveness_score=61,
                environment_score=59,
            ),
        ],
        active_issues=[
            MissionIssueContext(
                id=ISSUE_ID,
                public_reference="CP-20260627-00000001",
                title="Broken streetlight outside park",
                ai_summary="A public streetlight outage near a park creates visibility risk.",
                category="streetlight",
                severity="high",
                urgency_level="urgent",
                suggested_department="Electricity / Streetlighting",
                location="Sector 12",
                landmark="Central Park",
                status="community_verified",
                area_id=AREA_ID,
                age_days=2,
            ),
        ],
        existing_active_missions=[],
    )


def valid_payload(*, area_id: UUID = AREA_ID, issue_id: UUID = ISSUE_ID) -> str:
    return f"""
    {{
      "missions": [
        {{
          "title": "Verify Sector 12 streetlights",
          "area_id": "{area_id}",
          "mission_type": "verification",
          "goal_description": "Ask residents to safely confirm whether streetlights are working.",
          "target_count": 5,
          "category": "streetlight",
          "reward": {{"points": 20, "score_key": "participation"}},
          "ai_reason": "A verified streetlight report needs more safe observations.",
          "linked_issue_ids": ["{issue_id}"],
          "expires_in_days": 7
        }}
      ]
    }}
    """


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


@pytest.fixture(autouse=True)
def fake_gemini_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.mission_generation.genai.Client", FakeGenAIClient)


def settings() -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-mission-test",
    )


def test_demo_mission_generator_creates_safe_draft_candidate() -> None:
    result = DemoCivicMissionGenerator().generate(mission_context())

    assert result.missions[0].area_id == AREA_ID
    assert result.missions[0].linked_issue_ids == [ISSUE_ID]
    assert result.missions[0].mission_type == MissionType.VERIFICATION
    assert result.missions[0].category == IssueCategory.STREETLIGHT


def test_mission_generation_prompt_excludes_private_field_names() -> None:
    prompt = mission_generation_prompt(mission_context())

    assert "Broken streetlight outside park" in prompt
    assert '"missions"' in prompt
    assert "Do not add keys outside this shape" in prompt
    assert "citizen_name" not in prompt
    assert "citizen_contact" not in prompt
    assert "actor_hash" not in prompt
    assert "image_key" not in prompt
    assert "session_token" not in prompt
    assert "private@example.com" not in prompt


def test_gemini_mission_generator_parses_valid_json() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=valid_payload())

    result = GeminiCivicMissionGenerator(settings()).generate(mission_context())

    assert result.missions[0].title == "Verify Sector 12 streetlights"
    assert result.missions[0].area_id == AREA_ID
    assert FakeGenAIClient.latest_models is not None
    call = FakeGenAIClient.latest_models.calls[0]
    assert call["model"] == "gemini-mission-test"
    assert "Broken streetlight outside park" in str(call["contents"])


def test_gemini_mission_generator_rejects_malformed_json() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text='{"missions": []}')

    with pytest.raises(AppError) as caught:
        GeminiCivicMissionGenerator(settings()).generate(mission_context())

    assert caught.value.code == "ai_invalid_response"
    assert caught.value.status_code == 502


def test_gemini_mission_generator_rejects_unknown_area_ids() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=valid_payload(area_id=UUID(int=999)))

    with pytest.raises(AppError) as caught:
        GeminiCivicMissionGenerator(settings()).generate(mission_context())

    assert caught.value.code == "ai_invalid_response"
    assert "area" in caught.value.message


def test_gemini_mission_generator_rejects_unknown_issue_ids() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=valid_payload(issue_id=UUID(int=999)))

    with pytest.raises(AppError) as caught:
        GeminiCivicMissionGenerator(settings()).generate(mission_context())

    assert caught.value.code == "ai_invalid_response"
    assert "issue" in caught.value.message


def test_gemini_mission_generator_returns_safe_provider_error() -> None:
    FakeGenAIClient.next_response = TimeoutError("timeout with api key details")

    with pytest.raises(AppError) as caught:
        GeminiCivicMissionGenerator(settings()).generate(mission_context())

    assert caught.value.code == "mission_ai_unavailable"
    assert caught.value.status_code == 503
    assert "api key" not in caught.value.message.lower()


def test_safe_fallback_mission_generator_uses_demo_when_gemini_is_unavailable() -> None:
    FakeGenAIClient.next_response = TimeoutError("network unreachable")
    generator = SafeFallbackMissionGenerator(
        GeminiCivicMissionGenerator(settings()),
        DemoCivicMissionGenerator(),
    )

    result = generator.generate(mission_context())

    assert result.missions[0].linked_issue_ids == [ISSUE_ID]
    assert generator.model_name == "demo-civic-mission-generator-v1"


class FakeMissionRepository:
    def __init__(self, context: MissionContext) -> None:
        self.context = context
        self.saved: list[Mission] = []
        self.area = Area(
            id=AREA_ID,
            name="Sector 12",
            slug="civicpulse-city-sector-12",
            city="CivicPulse City",
        )

    def generation_context(self, *, issue_limit: int = 50) -> MissionContext:
        return self.context

    def add(self, mission: Mission) -> Mission:
        mission.id = uuid4()
        mission.area = self.area
        mission.created_at = datetime.now(UTC)
        mission.updated_at = mission.created_at
        self.saved.append(mission)
        return mission

    def get_detail(self, mission_id: UUID) -> Mission | None:
        return next((mission for mission in self.saved if mission.id == mission_id), None)

    def list_admin(self) -> list[Mission]:
        return self.saved

    def list_public(self) -> list[Mission]:
        return []

    def get_public_detail(self, mission_id: UUID) -> Mission | None:
        return None

    def flush(self) -> None:
        return None


class StaticMissionGenerator:
    model_name = "gemini-mission-test"

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        return MissionGenerationPayload.model_validate_json(valid_payload())


class UnknownAreaGenerator:
    model_name = "gemini-mission-test"

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        return MissionGenerationPayload.model_validate_json(valid_payload(area_id=UUID(int=999)))


def test_mission_generation_service_saves_generated_missions_as_drafts() -> None:
    repository = FakeMissionRepository(mission_context())

    response = MissionGenerationService(repository, StaticMissionGenerator()).generate_drafts()

    assert response.model_used == "gemini-mission-test"
    assert response.created_drafts[0].status == MissionStatus.DRAFT
    assert response.created_drafts[0].published_at is None
    assert response.created_drafts[0].linked_issue_ids == [ISSUE_ID]
    assert repository.saved[0].model_used == "gemini-mission-test"


def test_mission_generation_service_skips_duplicate_drafts() -> None:
    repository = FakeMissionRepository(mission_context())
    existing = Mission(
        id=UUID(int=20),
        title="Document Sector 12 streetlights",
        area=repository.area,
        area_id=repository.area.id,
        mission_type=MissionType.VERIFICATION,
        status=MissionStatus.DRAFT,
        goal_description="Ask residents to safely confirm the streetlight issue.",
        target_count=5,
        progress_count=0,
        category=IssueCategory.STREETLIGHT,
        reward_json={"points": 20, "score_key": "participation"},
        ai_reason="Existing draft mission.",
        linked_issue_ids_json=[str(ISSUE_ID)],
        model_used="existing",
        raw_response_json={},
        expires_at=datetime.now(UTC),
        published_at=None,
        completed_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.saved.append(existing)

    response = MissionGenerationService(repository, StaticMissionGenerator()).generate_drafts()

    assert response.created_drafts == []
    assert repository.saved == [existing]


def test_mission_generation_service_rejects_unknown_ids_before_saving() -> None:
    repository = FakeMissionRepository(mission_context())

    with pytest.raises(AppError) as caught:
        MissionGenerationService(repository, UnknownAreaGenerator()).generate_drafts()

    assert caught.value.code == "ai_invalid_response"
    assert repository.saved == []


def test_generated_mission_candidate_forbids_unexpected_keys() -> None:
    payload = {
        "title": "Verify Sector 12 streetlights",
        "area_id": str(AREA_ID),
        "mission_type": "verification",
        "goal_description": "Ask residents to safely confirm whether streetlights are working.",
        "target_count": 5,
        "category": "streetlight",
        "reward": {"points": 20},
        "ai_reason": "A verified streetlight issue needs extra public observations.",
        "linked_issue_ids": [str(ISSUE_ID)],
        "expires_in_days": 7,
        "citizen_contact": "private@example.com",
    }

    with pytest.raises(ValueError):
        GeneratedMissionCandidate.model_validate(payload)
