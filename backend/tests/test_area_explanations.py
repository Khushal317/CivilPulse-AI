from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.domain.areas import area_slug
from app.models.area import Area
from app.services.area_explanations import (
    DemoCivicAreaExplainer,
    GeminiCivicAreaExplainer,
    SafeFallbackAreaExplainer,
    area_explanation_prompt,
)


def make_area() -> Area:
    return Area(
        id=UUID(int=1),
        name="Sector 12",
        slug=area_slug("Sector 12"),
        city="CivicPulse City",
        overall_score=72,
        infrastructure_score=70,
        cleanliness_score=74,
        safety_score=66,
        participation_score=82,
        responsiveness_score=64,
        environment_score=73,
        rank=1,
        status_label="improving",
        created_at=datetime(2026, 6, 28, tzinfo=UTC),
        updated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )


def context():
    from app.services.area_explanations import AreaInsightInput

    area = make_area()
    return AreaInsightInput(
        area=area,
        open_issues=2,
        resolved_this_week=1,
        active_missions=1,
        total_issues=5,
        recent_score_events=[],
        active_issues=[],
    )


class FakeGeminiResponse:
    def __init__(self, *, text: str | None = None) -> None:
        self.parsed = None
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
    monkeypatch.setattr("app.services.area_explanations.genai.Client", FakeGenAIClient)


def settings() -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-area-test",
    )


def test_demo_area_explainer_returns_safe_actions() -> None:
    insight = DemoCivicAreaExplainer().explain(context())

    assert "Sector 12" in insight.explanation
    assert insight.next_best_actions
    assert insight.model_used == "demo-civic-area-explainer-v1"


def test_area_explanation_prompt_is_privacy_safe() -> None:
    prompt = area_explanation_prompt(context())

    assert "Sector 12" in prompt
    assert "citizen_name" not in prompt
    assert "citizen_contact" not in prompt
    assert "actor_hash" not in prompt
    assert "image_key" not in prompt
    assert "private@example.com" not in prompt


def test_gemini_area_explainer_parses_valid_json() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(
        text="""
        {
          "explanation": "Sector 12 is improving through public verification and active missions.",
          "next_best_actions": ["Verify safe public reports.", "Join active missions."]
        }
        """,
    )

    insight = GeminiCivicAreaExplainer(settings()).explain(context())

    assert insight.model_used == "gemini-area-test"
    assert insight.next_best_actions == ["Verify safe public reports.", "Join active missions."]
    assert FakeGenAIClient.latest_models is not None
    assert FakeGenAIClient.latest_models.calls[0]["model"] == "gemini-area-test"


def test_area_explainer_falls_back_safely_when_gemini_fails() -> None:
    FakeGenAIClient.next_response = TimeoutError("api key leaked details")
    explainer = SafeFallbackAreaExplainer(
        GeminiCivicAreaExplainer(settings()),
        DemoCivicAreaExplainer(),
    )

    insight = explainer.explain(context())

    assert insight.model_used == "demo-civic-area-explainer-v1"
    assert "api key" not in insight.explanation.lower()
