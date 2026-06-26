from typing import Any

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory
from app.schemas.issues import AIReportInput
from app.services import ai
from app.services.ai import GeminiCivicIssueAnalyzer


def report_input() -> AIReportInput:
    return AIReportInput(
        original_description="There is a deep pothole near the school gate.",
        location="Sector 12",
        landmark="City Public School",
        preferred_category=IssueCategory.ROAD_DAMAGE,
        urgency_note="Children cross here every morning.",
    )


def analysis_payload() -> str:
    return """
    {
      "title": "Deep pothole near school gate",
      "ai_summary": "A deep pothole creates a road safety concern near a school gate.",
      "category": "road_damage",
      "severity": "high",
      "urgency_level": "urgent",
      "urgency_reason": "Children and two-wheel riders use this route every day.",
      "suggested_department": "Public Works",
      "safety_risk": "Riders may lose control near the school entrance.",
      "citizen_explanation": "Review this structured report before publishing.",
      "suggested_next_action": "Publish the report for community verification."
    }
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
    monkeypatch.setattr(ai.genai, "Client", FakeGenAIClient)


def settings() -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-test",
    )


def test_gemini_parses_structured_json_text() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=analysis_payload())

    result = GeminiCivicIssueAnalyzer(settings()).analyze(
        report_input(),
        b"image-bytes",
        "image/png",
    )

    assert result.title == "Deep pothole near school gate"
    assert result.category is IssueCategory.ROAD_DAMAGE
    assert FakeGenAIClient.latest_models is not None
    call = FakeGenAIClient.latest_models.calls[0]
    assert call["model"] == "gemini-test"
    assert "City Public School" in str(call["contents"])


def test_gemini_malformed_structured_output_returns_safe_error() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text='{"title": "too short"}')

    with pytest.raises(AppError) as caught:
        GeminiCivicIssueAnalyzer(settings()).analyze(report_input(), b"image", "image/png")

    assert caught.value.code == "ai_invalid_response"
    assert caught.value.status_code == 502


def test_gemini_transport_failure_returns_safe_error() -> None:
    FakeGenAIClient.next_response = TimeoutError("network timeout with private details")

    with pytest.raises(AppError) as caught:
        GeminiCivicIssueAnalyzer(settings()).analyze(report_input(), b"image", "image/png")

    assert caught.value.code == "ai_unavailable"
    assert caught.value.status_code == 503
    assert "private details" not in caught.value.message
