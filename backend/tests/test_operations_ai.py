from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.operations import OperationsIssueInput
from app.services.operations_ai import (
    OPERATIONS_SYSTEM_INSTRUCTION,
    DemoCivicOperationsAnalyzer,
    GeminiCivicOperationsAnalyzer,
    SafeFallbackOperationsAnalyzer,
    operations_prompt,
)

DEFAULT_ISSUE_ID = UUID(int=1)


def operations_issue(
    number: int = 1,
    *,
    severity: IssueSeverity = IssueSeverity.HIGH,
    status: IssueStatus = IssueStatus.COMMUNITY_VERIFIED,
) -> OperationsIssueInput:
    return OperationsIssueInput(
        issue_id=UUID(int=number),
        public_reference=f"CP-20260626-{number:08d}",
        title=f"Severe pothole near school gate {number}",
        category=IssueCategory.ROAD_DAMAGE,
        department="Public Works / Road Maintenance",
        severity=severity,
        status=status,
        location="Sector 12",
        landmark="City Public School",
        verification_count=5,
        unresolved_count=3,
        fixed_count=0,
        incorrect_count=0,
        created_at=datetime(2026, 6, 24, 10, tzinfo=UTC),
        age_hours=48,
        age_days=2,
        summary="Large pothole near school gate causing risk to children and riders.",
        latest_admin_update="Escalated for inspection.",
    )


def valid_payload(issue_id: UUID | None = None) -> str:
    selected_issue_id = issue_id or DEFAULT_ISSUE_ID
    return f"""
    {{
      "executive_summary": "One high-risk road issue needs immediate administrator review.",
      "urgent_issues": [
        {{
          "issue_id": "{selected_issue_id}",
          "public_reference": "CP-20260626-00000001",
          "title": "Severe pothole near school gate 1",
          "location": "Sector 12, near City Public School",
          "department": "Public Works / Road Maintenance",
          "severity": "high",
          "priority_reason": "High severity and multiple community confirmations near a school.",
          "recommended_action": "Inspect and temporarily barricade the area.",
          "suggested_time_window": "Within 24 hours"
        }}
      ],
      "duplicate_clusters": [],
      "area_hotspots": [
        {{
          "area": "Sector 12",
          "issue_count": 1,
          "main_categories": ["road_damage"],
          "risk_level": "high",
          "insight": "School-zone road damage should be reviewed quickly."
        }}
      ],
      "department_priorities": [
        {{
          "department": "Public Works / Road Maintenance",
          "open_issues": 1,
          "high_priority_count": 1,
          "recommended_focus": "Prioritize the verified school-zone pothole."
        }}
      ],
      "escalation_messages": [
        {{
          "department": "Public Works / Road Maintenance",
          "issue_id": "{selected_issue_id}",
          "public_reference": "CP-20260626-00000001",
          "issue_title": "Severe pothole near school gate 1",
          "message": "Urgent inspection requested for a verified pothole near City Public School."
        }}
      ],
      "predicted_risks": [
        {{
          "issue_id": "{selected_issue_id}",
          "public_reference": "CP-20260626-00000001",
          "issue_title": "Severe pothole near school gate 1",
          "risk": "If ignored, riders or children may be injured.",
          "risk_level": "high",
          "preventive_action": "Barricade the area and schedule urgent road repair."
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
    monkeypatch.setattr("app.services.operations_ai.genai.Client", FakeGenAIClient)


def settings() -> Settings:
    return Settings(
        ai_provider="gemini",
        gemini_api_key="test-gemini-key",
        gemini_model="gemini-operations-test",
    )


def test_demo_operations_analyzer_returns_empty_report_without_issues() -> None:
    result = DemoCivicOperationsAnalyzer().analyze([])

    assert result.total_issues_analyzed == 0
    assert result.model_used == "system-empty"
    assert result.urgent_issues == []
    assert "no active civic issues" in result.executive_summary.lower()


def test_demo_operations_analyzer_prioritizes_and_groups_issues() -> None:
    issues = [
        operations_issue(1, severity=IssueSeverity.HIGH),
        operations_issue(2, severity=IssueSeverity.CRITICAL),
        operations_issue(3, severity=IssueSeverity.MEDIUM),
    ]

    result = DemoCivicOperationsAnalyzer().analyze(issues)

    assert result.total_issues_analyzed == 3
    assert result.model_used == "demo-civic-operations-agent-v1"
    assert result.urgent_issues[0].issue_id == UUID(int=2)
    assert result.department_priorities[0].open_issues == 3
    assert result.escalation_messages[0].message
    assert result.predicted_risks[0].risk_level in {"high", "critical"}


def test_operations_prompt_excludes_private_field_names() -> None:
    prompt = operations_prompt([operations_issue()])

    assert "Severe pothole near school gate" in prompt
    assert '"executive_summary"' in prompt
    assert '"urgent_issues"' in prompt
    assert "Do not add keys outside this shape" in prompt
    assert "citizen_contact" not in prompt
    assert "citizen_name" not in prompt
    assert "actor_hash" not in prompt
    assert "image_key" not in prompt
    assert "private@example.com" not in prompt


def test_gemini_operations_analyzer_parses_valid_json() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=valid_payload())

    result = GeminiCivicOperationsAnalyzer(settings()).analyze([operations_issue()])

    assert result.model_used == "gemini-operations-test"
    assert result.total_issues_analyzed == 1
    assert result.urgent_issues[0].issue_id == UUID(int=1)
    assert result.area_hotspots[0].area == "Sector 12"
    assert FakeGenAIClient.latest_models is not None
    call = FakeGenAIClient.latest_models.calls[0]
    assert call["model"] == "gemini-operations-test"
    assert call["config"].response_schema is None
    assert "Never invent issue IDs" in OPERATIONS_SYSTEM_INSTRUCTION
    assert "City Public School" in str(call["contents"])


def test_gemini_operations_analyzer_rejects_malformed_json() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text='{"executive_summary": "too thin"}')

    with pytest.raises(AppError) as caught:
        GeminiCivicOperationsAnalyzer(settings()).analyze([operations_issue()])

    assert caught.value.code == "ai_invalid_response"
    assert caught.value.status_code == 502


def test_gemini_operations_analyzer_rejects_unknown_issue_ids() -> None:
    FakeGenAIClient.next_response = FakeGeminiResponse(text=valid_payload(UUID(int=999)))

    with pytest.raises(AppError) as caught:
        GeminiCivicOperationsAnalyzer(settings()).analyze([operations_issue()])

    assert caught.value.code == "ai_invalid_response"
    assert "not provided" in caught.value.message


def test_gemini_operations_analyzer_returns_safe_provider_error() -> None:
    FakeGenAIClient.next_response = TimeoutError("timeout with api key details")

    with pytest.raises(AppError) as caught:
        GeminiCivicOperationsAnalyzer(settings()).analyze([operations_issue()])

    assert caught.value.code == "operations_ai_unavailable"
    assert caught.value.status_code == 503
    assert "api key" not in caught.value.message.lower()


def test_gemini_operations_analyzer_skips_provider_when_no_active_issues() -> None:
    FakeGenAIClient.next_response = TimeoutError("should not be called")

    result = GeminiCivicOperationsAnalyzer(settings()).analyze([])

    assert result.model_used == "system-empty"
    assert FakeGenAIClient.latest_models is not None
    assert FakeGenAIClient.latest_models.calls == []


def test_safe_fallback_operations_analyzer_uses_demo_when_gemini_is_unavailable() -> None:
    FakeGenAIClient.next_response = TimeoutError("network unreachable")
    analyzer = SafeFallbackOperationsAnalyzer(
        GeminiCivicOperationsAnalyzer(settings()),
        DemoCivicOperationsAnalyzer(),
    )

    result = analyzer.analyze([operations_issue()])

    assert result.model_used == "demo-civic-operations-agent-v1"
    assert result.total_issues_analyzed == 1
    assert analyzer.model_name == "demo-civic-operations-agent-v1"
