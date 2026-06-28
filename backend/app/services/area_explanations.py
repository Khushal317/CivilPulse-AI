import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import types
from pydantic import ConfigDict, Field

from app.core.config import Settings, get_settings
from app.models.area import Area
from app.models.area_score_event import AreaScoreEvent
from app.models.issue import Issue
from app.schemas.areas import AreaCivicGenomeProfile, AreaInsightResponse
from app.schemas.common import APIModel

AREA_EXPLANATION_SYSTEM_INSTRUCTION = """
You are CivicPulse AI's Civic Genome Explainer.

Your job:
- Explain a neighborhood Civic Genome in plain, positive, non-stigmatizing language.
- Suggest safe next-best civic actions residents and admins can take.
- Use only the public aggregate data provided.

Rules:
- Return valid JSON only.
- Never include private citizen details, contacts, image keys, actor hashes, sessions, or secrets.
- Never shame or label a neighborhood as bad.
- Do not claim official government action was taken unless provided in the data.
- Keep suggestions safe: observe, verify, report, coordinate, and follow official channels.
""".strip()


class AreaInsightPayload(APIModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    explanation: str = Field(min_length=40, max_length=900)
    next_best_actions: list[str] = Field(min_length=1, max_length=5)


@dataclass(frozen=True, slots=True)
class AreaInsightInput:
    area: Area
    civic_genome: AreaCivicGenomeProfile
    open_issues: int
    resolved_this_week: int
    active_missions: int
    total_issues: int
    recent_score_events: list[AreaScoreEvent]
    active_issues: list[Issue]


class CivicAreaExplainer(Protocol):
    model_name: str

    def explain(self, context: AreaInsightInput) -> AreaInsightResponse: ...


def _event_payload(event: AreaScoreEvent) -> dict[str, object]:
    return {
        "event_type": event.event_type,
        "score_key": event.score_key.value,
        "score_change": event.score_change,
        "previous_score": event.previous_score,
        "new_score": event.new_score,
        "reason": event.reason,
    }


def _issue_payload(issue: Issue) -> dict[str, object]:
    return {
        "public_reference": issue.public_reference,
        "title": issue.title,
        "category": issue.category.value,
        "severity": issue.severity.value,
        "status": issue.status.value,
        "location": issue.location,
        "landmark": issue.landmark,
    }


def area_explanation_prompt(context: AreaInsightInput) -> str:
    area = context.area
    payload = {
        "area": {
            "name": area.name,
            "city": area.city,
            "rank": area.rank,
            "status_label": area.status_label,
            "scores": {
                "civic_health": context.civic_genome.civic_health_score,
                "community_power": context.civic_genome.community_power_score,
                "confidence": context.civic_genome.confidence_level,
                "confidence_reason": context.civic_genome.confidence_reason,
                "score_limit_reasons": context.civic_genome.score_limit_reasons,
                "infrastructure": area.infrastructure_score,
                "cleanliness": area.cleanliness_score,
                "safety": area.safety_score,
                "participation": area.participation_score,
                "responsiveness": area.responsiveness_score,
                "environment": area.environment_score,
            },
            "open_issues": context.open_issues,
            "resolved_this_week": context.resolved_this_week,
            "active_missions": context.active_missions,
            "total_issues": context.total_issues,
        },
        "recent_score_events": [
            _event_payload(event) for event in context.recent_score_events[:8]
        ],
        "active_issues": [_issue_payload(issue) for issue in context.active_issues[:6]],
    }
    return (
        "Explain this CivicPulse AI neighborhood Civic Genome and return exactly one JSON "
        "object. Do not wrap in markdown or code fences.\n"
        "Do not include private citizen details, contacts, actor hashes, image identifiers, "
        "sessions, secrets, or credentials.\n"
        "Use constructive language and avoid harmful neighborhood labels.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "explanation": "plain-language explanation of Civic Health, Community '
        'Power, confidence, and score limits",\n'
        '  "next_best_actions": ["safe useful next action", "another action"]\n'
        "}\n\n"
        f"Public Civic Genome context JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


class DemoCivicAreaExplainer:
    model_name = "demo-civic-area-explainer-v1"

    def explain(self, context: AreaInsightInput) -> AreaInsightResponse:
        area = context.area
        civic_health_scores = (
            ("infrastructure", area.infrastructure_score),
            ("cleanliness", area.cleanliness_score),
            ("safety", area.safety_score),
            ("responsiveness", area.responsiveness_score),
            ("environment", area.environment_score),
        )
        strongest_score = max(
            (
                *civic_health_scores,
                ("community power", context.civic_genome.community_power_score),
            ),
            key=lambda item: item[1],
        )
        lowest_health_score = min(civic_health_scores, key=lambda item: item[1])
        actions = [
            (
                f"Review the newest public issues in {area.name} and verify what "
                "residents can safely observe."
            ),
            "Join or complete active community missions to strengthen useful public signals.",
            (
                f"Focus next on {lowest_health_score[0].replace('_', ' ')} because it is "
                "the area's lowest current Civic Health signal."
            ),
        ]
        if context.open_issues:
            actions.append("Coordinate admin follow-up for high-priority open issues.")
        return AreaInsightResponse(
            explanation=(
                f"{area.name} has a Civic Health Score of "
                f"{context.civic_genome.civic_health_score} and a Community Power Score of "
                f"{context.civic_genome.community_power_score}. "
                f"Its strongest current signal is {strongest_score[0].replace('_', ' ')} "
                f"at {strongest_score[1]}, while "
                f"{lowest_health_score[0].replace('_', ' ')} at {lowest_health_score[1]} "
                "is the clearest Civic Health improvement opportunity. "
                f"Confidence is {context.civic_genome.confidence_level}: "
                f"{context.civic_genome.confidence_reason} "
                f"There are {context.open_issues} open issue(s), {context.resolved_this_week} "
                f"resolved this week, and {context.active_missions} active mission(s)."
            ),
            next_best_actions=actions[:5],
            model_used=self.model_name,
        )


class GeminiCivicAreaExplainer:
    def __init__(self, settings: Settings) -> None:
        assert settings.gemini_api_key is not None
        self.model_name = settings.gemini_model
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1_000),
        )

    def explain(self, context: AreaInsightInput) -> AreaInsightResponse:
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=types.Content(
                role="user",
                parts=[types.Part.from_text(text=area_explanation_prompt(context))],
            ),
            config=types.GenerateContentConfig(
                system_instruction=AREA_EXPLANATION_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        if isinstance(response.parsed, AreaInsightPayload):
            payload = response.parsed
        elif response.text:
            payload = AreaInsightPayload.model_validate_json(response.text)
        else:
            raise ValueError("Gemini returned no Civic Genome explanation")
        return AreaInsightResponse(
            explanation=payload.explanation,
            next_best_actions=payload.next_best_actions,
            model_used=self.model_name,
        )


class SafeFallbackAreaExplainer:
    def __init__(self, primary: CivicAreaExplainer, fallback: CivicAreaExplainer) -> None:
        self.model_name = primary.model_name
        self._primary = primary
        self._fallback = fallback
        self._cache: dict[tuple[object, ...], AreaInsightResponse] = {}

    def explain(self, context: AreaInsightInput) -> AreaInsightResponse:
        cache_key = (
            context.area.id,
            context.area.updated_at,
            context.civic_genome.civic_health_score,
            context.civic_genome.community_power_score,
            context.civic_genome.confidence_level,
            tuple(context.civic_genome.score_limit_reasons),
            context.open_issues,
            context.resolved_this_week,
            context.active_missions,
            context.total_issues,
            len(context.recent_score_events),
            len(context.active_issues),
        )
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            insight = self._primary.explain(context)
        except Exception:
            insight = self._fallback.explain(context)
        self._cache[cache_key] = insight
        return insight


@lru_cache
def get_civic_area_explainer() -> CivicAreaExplainer:
    settings = get_settings()
    fallback = DemoCivicAreaExplainer()
    if settings.ai_provider == "gemini":
        return SafeFallbackAreaExplainer(GeminiCivicAreaExplainer(settings), fallback)
    return SafeFallbackAreaExplainer(fallback, fallback)
