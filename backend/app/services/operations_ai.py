import json
from collections import Counter
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.domain.enums import IssueSeverity
from app.schemas.operations import (
    AreaHotspot,
    DepartmentPriority,
    EscalationMessage,
    GeminiOperationsPayload,
    OperationsAnalysis,
    OperationsIssueInput,
    PredictedRisk,
    UrgentIssueRecommendation,
)

OPERATIONS_SYSTEM_INSTRUCTION = """
You are CivicPulse AI's Civic Operations Agent, a civic operations analyst for
municipal administrators.

Your job:
- Analyze only the active civic issues provided in the prompt.
- Rank urgency.
- Detect possible duplicate reports.
- Identify area hotspots.
- Group department workload.
- Draft escalation messages.
- Predict risks if serious issues are ignored.

Rules:
- Return valid JSON only.
- Never invent issue IDs, public references, departments, locations, or issues.
- Never mark issues resolved or imply work has been accepted or completed.
- Do not send messages or claim messages were sent.
- Use only provided data and state uncertainty when evidence is weak.
- Recommendations are advisory; an administrator remains accountable for decisions.
""".strip()


class CivicOperationsAnalyzer(Protocol):
    model_name: str

    def analyze(self, issues: list[OperationsIssueInput]) -> OperationsAnalysis: ...


def empty_operations_analysis(model_used: str = "system-empty") -> OperationsAnalysis:
    return OperationsAnalysis(
        total_issues_analyzed=0,
        model_used=model_used,
        executive_summary="There are no active civic issues to analyze right now.",
        raw_response={
            "executive_summary": "There are no active civic issues to analyze right now.",
            "urgent_issues": [],
            "duplicate_clusters": [],
            "area_hotspots": [],
            "department_priorities": [],
            "escalation_messages": [],
            "predicted_risks": [],
        },
    )


def _issue_ids(issues: list[OperationsIssueInput]) -> set[UUID]:
    return {issue.issue_id for issue in issues}


def _validate_referenced_issues(
    analysis: OperationsAnalysis,
    allowed_issue_ids: set[UUID],
) -> None:
    referenced_ids: set[UUID] = set()
    referenced_ids.update(issue.issue_id for issue in analysis.urgent_issues)
    referenced_ids.update(message.issue_id for message in analysis.escalation_messages)
    referenced_ids.update(risk.issue_id for risk in analysis.predicted_risks)
    for cluster in analysis.duplicate_clusters:
        referenced_ids.update(issue.issue_id for issue in cluster.issues)

    unknown_ids = referenced_ids - allowed_issue_ids
    if unknown_ids:
        raise AppError(
            code="ai_invalid_response",
            message="The AI response referenced an issue that was not provided.",
            status_code=502,
        )


def _analysis_from_payload(
    payload: GeminiOperationsPayload,
    *,
    model_used: str,
    total_issues_analyzed: int,
    raw_response: dict[str, object],
    allowed_issue_ids: set[UUID],
) -> OperationsAnalysis:
    analysis = OperationsAnalysis(
        total_issues_analyzed=total_issues_analyzed,
        model_used=model_used,
        executive_summary=payload.executive_summary,
        urgent_issues=payload.urgent_issues,
        duplicate_clusters=payload.duplicate_clusters,
        area_hotspots=payload.area_hotspots,
        department_priorities=payload.department_priorities,
        escalation_messages=payload.escalation_messages,
        predicted_risks=payload.predicted_risks,
        raw_response=raw_response,
    )
    _validate_referenced_issues(analysis, allowed_issue_ids)
    return analysis


def operations_prompt(issues: list[OperationsIssueInput]) -> str:
    payload = [issue.model_dump(mode="json") for issue in issues]
    return (
        "Analyze the following active CivicPulse AI issues and return the required JSON.\n"
        "Only reference issue IDs and public references from this list.\n"
        "Do not include citizen names, contacts, image keys, sessions, or secrets.\n\n"
        f"Active issues JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


class DemoCivicOperationsAnalyzer:
    model_name = "demo-civic-operations-agent-v1"

    def analyze(self, issues: list[OperationsIssueInput]) -> OperationsAnalysis:
        if not issues:
            return empty_operations_analysis()

        sorted_issues = sorted(
            issues,
            key=lambda issue: (
                self._severity_rank(issue.severity),
                issue.verification_count,
                issue.unresolved_count,
                issue.age_hours,
            ),
            reverse=True,
        )
        urgent = sorted_issues[:5]
        departments = Counter(issue.department for issue in issues)
        locations = Counter(issue.location for issue in issues)
        categories = Counter(issue.category for issue in issues)
        high_priority = {
            department: sum(
                1
                for issue in issues
                if issue.department == department
                and issue.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)
            )
            for department in departments
        }
        payload = GeminiOperationsPayload(
            executive_summary=(
                f"{len(issues)} active civic issues need administrator attention. "
                f"{categories.most_common(1)[0][0].value.replace('_', ' ').title()} is the most "
                f"common category, and {locations.most_common(1)[0][0]} appears most often."
            ),
            urgent_issues=[
                UrgentIssueRecommendation(
                    issue_id=issue.issue_id,
                    public_reference=issue.public_reference,
                    title=issue.title,
                    location=self._location(issue),
                    department=issue.department,
                    severity=issue.severity,
                    priority_reason=(
                        "High operational priority based on severity, community signals, "
                        "and issue age."
                    ),
                    recommended_action=(
                        "Review the issue and coordinate the responsible department."
                    ),
                    suggested_time_window=(
                        "Within 24 hours"
                        if issue.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)
                        else "Within 72 hours"
                    ),
                )
                for issue in urgent
            ],
            area_hotspots=[
                AreaHotspot(
                    area=area,
                    issue_count=count,
                    main_categories=[
                        category
                        for category, _count in Counter(
                            issue.category for issue in issues if issue.location == area
                        ).most_common(3)
                    ],
                    risk_level="high" if count >= 3 else "medium",
                    insight=(
                        f"{area} has {count} active issue(s), suggesting a localized "
                        "maintenance or response pattern to review."
                    ),
                )
                for area, count in locations.most_common(5)
            ],
            department_priorities=[
                DepartmentPriority(
                    department=department,
                    open_issues=count,
                    high_priority_count=high_priority[department],
                    recommended_focus=(
                        "Prioritize high-severity and community-verified issues first."
                    ),
                )
                for department, count in departments.most_common()
            ],
            escalation_messages=[
                EscalationMessage(
                    department=issue.department,
                    issue_id=issue.issue_id,
                    public_reference=issue.public_reference,
                    issue_title=issue.title,
                    message=(
                        f"Please review {issue.public_reference}: {issue.title} at "
                        f"{self._location(issue)}. Community and severity signals suggest "
                        "administrator follow-up is needed."
                    ),
                )
                for issue in urgent
            ],
            predicted_risks=[
                PredictedRisk(
                    issue_id=issue.issue_id,
                    public_reference=issue.public_reference,
                    issue_title=issue.title,
                    risk=(
                        "If ignored, this issue may worsen public inconvenience or safety risk."
                    ),
                    risk_level="high"
                    if issue.severity in (IssueSeverity.HIGH, IssueSeverity.CRITICAL)
                    else "medium",
                    preventive_action="Review the issue and arrange timely mitigation.",
                )
                for issue in urgent
            ],
        )
        return _analysis_from_payload(
            payload,
            model_used=self.model_name,
            total_issues_analyzed=len(issues),
            raw_response=payload.model_dump(mode="json"),
            allowed_issue_ids=_issue_ids(issues),
        )

    @staticmethod
    def _severity_rank(severity: IssueSeverity) -> int:
        return {
            IssueSeverity.LOW: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.HIGH: 3,
            IssueSeverity.CRITICAL: 4,
        }[severity]

    @staticmethod
    def _location(issue: OperationsIssueInput) -> str:
        if issue.landmark:
            return f"{issue.location}, near {issue.landmark}"
        return issue.location


class GeminiCivicOperationsAnalyzer:
    def __init__(self, settings: Settings) -> None:
        assert settings.gemini_api_key is not None
        self.model_name = settings.gemini_model
        self._max_attempts = settings.gemini_max_attempts
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1_000),
        )

    def analyze(self, issues: list[OperationsIssueInput]) -> OperationsAnalysis:
        if not issues:
            return empty_operations_analysis()

        last_error: Exception | None = None
        for _attempt in range(self._max_attempts):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=operations_prompt(issues))],
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction=OPERATIONS_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=GeminiOperationsPayload,
                        temperature=0.1,
                    ),
                )
                if isinstance(response.parsed, GeminiOperationsPayload):
                    payload = response.parsed
                    raw_response = payload.model_dump(mode="json")
                elif response.text:
                    payload = GeminiOperationsPayload.model_validate_json(response.text)
                    raw_response = payload.model_dump(mode="json")
                else:
                    raise ValueError("Gemini returned no civic operations content")
                return _analysis_from_payload(
                    payload,
                    model_used=self.model_name,
                    total_issues_analyzed=len(issues),
                    raw_response=raw_response,
                    allowed_issue_ids=_issue_ids(issues),
                )
            except AppError:
                raise
            except (ValidationError, ValueError) as exc:
                last_error = exc
                continue
            except Exception as exc:
                raise AppError(
                    code="operations_ai_unavailable",
                    message=(
                        "The Civic Operations Agent could not analyze city issues right now. "
                        "Please try again."
                    ),
                    status_code=503,
                ) from exc

        raise AppError(
            code="ai_invalid_response",
            message="The Civic Operations Agent response could not be validated.",
            status_code=502,
        ) from last_error


@lru_cache
def get_civic_operations_analyzer() -> CivicOperationsAnalyzer:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        return GeminiCivicOperationsAnalyzer(settings)
    return DemoCivicOperationsAnalyzer()
