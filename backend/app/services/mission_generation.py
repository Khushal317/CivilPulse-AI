import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory
from app.domain.mission_titles import mission_duplicate_key
from app.domain.missions import MissionStatus, MissionType
from app.models.mission import Mission
from app.repositories.missions import MissionContext, MissionRepository
from app.schemas.missions import (
    GeneratedMissionCandidate,
    MissionGenerationPayload,
    MissionGenerationResponse,
)
from app.services.missions import mission_detail

MISSION_GENERATION_SYSTEM_INSTRUCTION = """
You are CivicPulse AI's Community Mission Designer, an assistant for municipal
administrators and civic communities.

Your job:
- Convert public civic issue patterns into small, useful community missions.
- Generate draft missions only; never claim missions are published or completed.
- Use only area IDs and issue IDs provided in the prompt.
- Keep missions safe, concrete, measurable, and locally actionable.

Rules:
- Return valid JSON only.
- Never invent area IDs, issue IDs, public references, or city details.
- Never ask citizens to do dangerous work, enter private property, confront people, or replace
  official repair crews.
- Do not include private citizen details, contact information, image identifiers, actor hashes,
  sessions, secrets, or internal credentials.
- Recommendations are advisory; an administrator remains accountable for publishing decisions.
""".strip()


class CivicMissionGenerator(Protocol):
    model_name: str

    def generate(self, context: MissionContext) -> MissionGenerationPayload: ...


def empty_mission_generation_response(model_used: str) -> MissionGenerationResponse:
    return MissionGenerationResponse(model_used=model_used, created_drafts=[])


def _context_payload(context: MissionContext) -> dict[str, object]:
    return {
        "areas": [asdict(area) for area in context.areas],
        "active_issues": [asdict(issue) for issue in context.active_issues],
        "existing_active_missions": [
            asdict(mission) for mission in context.existing_active_missions
        ],
    }


def mission_generation_prompt(context: MissionContext) -> str:
    payload = _context_payload(context)
    return (
        "Generate useful draft CivicPulse AI community missions from the provided public "
        "civic context and return exactly one JSON object.\n"
        "Do not wrap the response in markdown, code fences, or an outer key other than "
        "`missions`.\n"
        "Only reference area IDs and issue IDs from this context.\n"
        "Do not include private citizen details, contacts, actor hashes, image identifiers, "
        "sessions, secrets, or credentials.\n"
        "Prefer missions that help residents safely verify, observe, report, or coordinate "
        "non-hazardous civic evidence.\n"
        "Use only these mission_type values: verification, fix_confirmation, hotspot, "
        "category, volunteer.\n"
        "Use only these category values: road_damage, garbage_waste, streetlight, "
        "water_leakage, drainage_sewage, public_safety, other.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "missions": [\n'
        "    {\n"
        '      "title": "clear mission title",\n'
        '      "area_id": "provided area UUID",\n'
        '      "mission_type": "verification|fix_confirmation|hotspot|category|volunteer",\n'
        '      "goal_description": "safe measurable goal for residents",\n'
        '      "target_count": 5,\n'
        '      "category": "road_damage|null",\n'
        '      "reward": {"points": 20, "score_key": "participation"},\n'
        '      "ai_reason": "why this mission is useful now",\n'
        '      "linked_issue_ids": ["provided issue UUID"],\n'
        '      "expires_in_days": 7\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Create one to five missions. If evidence is weak, create fewer missions. "
        "Do not add keys outside this shape.\n\n"
        f"Public civic context JSON:\n{json.dumps(payload, ensure_ascii=False, default=str)}"
    )


def _allowed_area_ids(context: MissionContext) -> set[UUID]:
    return {area.id for area in context.areas}


def _allowed_issue_ids(context: MissionContext) -> set[UUID]:
    return {issue.id for issue in context.active_issues}


def validate_generated_missions(
    payload: MissionGenerationPayload,
    context: MissionContext,
) -> None:
    allowed_area_ids = _allowed_area_ids(context)
    allowed_issue_ids = _allowed_issue_ids(context)
    referenced_area_ids = {mission.area_id for mission in payload.missions}
    referenced_issue_ids = {
        issue_id for mission in payload.missions for issue_id in mission.linked_issue_ids
    }

    if referenced_area_ids - allowed_area_ids:
        raise AppError(
            code="ai_invalid_response",
            message="The AI mission response referenced an area that was not provided.",
            status_code=502,
        )
    if referenced_issue_ids - allowed_issue_ids:
        raise AppError(
            code="ai_invalid_response",
            message="The AI mission response referenced an issue that was not provided.",
            status_code=502,
        )


class DemoCivicMissionGenerator:
    model_name = "demo-civic-mission-generator-v1"

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        if not context.areas:
            raise AppError(
                code="mission_context_empty",
                message="No neighborhood areas are available for mission generation.",
                status_code=409,
            )

        if context.active_issues:
            priority_issue = sorted(
                context.active_issues,
                key=lambda issue: (issue.age_days, issue.severity),
                reverse=True,
            )[0]
            area = next(
                (
                    candidate
                    for candidate in context.areas
                    if candidate.id == priority_issue.area_id
                ),
                context.areas[0],
            )
            return MissionGenerationPayload(
                missions=[
                    GeneratedMissionCandidate(
                        title=f"Verify {priority_issue.location} civic issue",
                        area_id=area.id,
                        mission_type=MissionType.VERIFICATION,
                        goal_description=(
                            "Ask nearby residents to safely confirm whether this public issue "
                            "is still visible and affecting the area."
                        ),
                        target_count=5,
                        category=IssueCategory(priority_issue.category),
                        reward={"points": 20, "score_key": "participation"},
                        ai_reason=(
                            f"{priority_issue.public_reference} is an active "
                            f"{priority_issue.category.replace('_', ' ')} report in "
                            f"{area.name}, so a short verification mission can improve "
                            "confidence before administrator action."
                        ),
                        linked_issue_ids=[priority_issue.id],
                        expires_in_days=7,
                    ),
                ],
            )

        area = sorted(context.areas, key=lambda candidate: candidate.overall_score)[0]
        return MissionGenerationPayload(
            missions=[
                GeneratedMissionCandidate(
                    title=f"Map safe observations in {area.name}",
                    area_id=area.id,
                    mission_type=MissionType.HOTSPOT,
                    goal_description=(
                        "Invite residents to submit safe public observations about recurring "
                        "civic issues in the neighborhood."
                    ),
                    target_count=10,
                    category=None,
                    reward={"points": 15, "score_key": "participation"},
                    ai_reason=(
                        f"{area.name} has room for stronger civic participation signals, "
                        "so a lightweight observation mission can improve local visibility."
                    ),
                    linked_issue_ids=[],
                    expires_in_days=10,
                ),
            ],
        )


class GeminiCivicMissionGenerator:
    def __init__(self, settings: Settings) -> None:
        assert settings.gemini_api_key is not None
        self.model_name = settings.gemini_model
        self._max_attempts = settings.gemini_max_attempts
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1_000),
        )

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        if not context.areas:
            raise AppError(
                code="mission_context_empty",
                message="No neighborhood areas are available for mission generation.",
                status_code=409,
            )

        last_error: Exception | None = None
        for _attempt in range(self._max_attempts):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=mission_generation_prompt(context))],
                    ),
                    config=types.GenerateContentConfig(
                        system_instruction=MISSION_GENERATION_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        temperature=0.2,
                    ),
                )
                if isinstance(response.parsed, MissionGenerationPayload):
                    payload = response.parsed
                elif response.text:
                    payload = MissionGenerationPayload.model_validate_json(response.text)
                else:
                    raise ValueError("Gemini returned no mission generation content")
                validate_generated_missions(payload, context)
                return payload
            except AppError:
                raise
            except (ValidationError, ValueError) as exc:
                last_error = exc
                continue
            except Exception as exc:
                raise AppError(
                    code="mission_ai_unavailable",
                    message=(
                        "The Civic Mission Generator could not create missions right now. "
                        "Please try again."
                    ),
                    status_code=503,
                ) from exc

        raise AppError(
            code="ai_invalid_response",
            message="The Civic Mission Generator response could not be validated.",
            status_code=502,
        ) from last_error


class SafeFallbackMissionGenerator:
    """Use Gemini mission ideas first, with a deterministic local fallback for demos."""

    def __init__(
        self,
        primary: CivicMissionGenerator,
        fallback: CivicMissionGenerator,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self.model_name = primary.model_name

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        self.model_name = self._primary.model_name
        try:
            return self._primary.generate(context)
        except AppError as exc:
            if exc.code not in {"mission_ai_unavailable", "ai_invalid_response"}:
                raise
        self.model_name = self._fallback.model_name
        return self._fallback.generate(context)


@lru_cache
def get_civic_mission_generator() -> CivicMissionGenerator:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        return SafeFallbackMissionGenerator(
            GeminiCivicMissionGenerator(settings),
            DemoCivicMissionGenerator(),
        )
    return DemoCivicMissionGenerator()


@dataclass(slots=True)
class MissionGenerationService:
    repository: MissionRepository
    generator: CivicMissionGenerator

    def generate_drafts(self) -> MissionGenerationResponse:
        existing_missions = self.repository.list_admin()
        existing_keys = {
            mission_duplicate_key(
                title=mission.title,
                area_id=mission.area_id,
                category=mission.category,
            )
            for mission in existing_missions
            if mission.status in (MissionStatus.DRAFT, MissionStatus.ACTIVE)
        }
        context = self.repository.generation_context()
        if not context.areas:
            return empty_mission_generation_response(self.generator.model_name)

        payload = self.generator.generate(context)
        validate_generated_missions(payload, context)

        raw_response = payload.model_dump(mode="json")
        now = datetime.now(UTC)
        created: list[Mission] = []
        for candidate in payload.missions:
            key = mission_duplicate_key(
                title=candidate.title,
                area_id=candidate.area_id,
                category=candidate.category,
            )
            if key in existing_keys:
                continue
            existing_keys.add(key)
            mission = Mission(
                title=candidate.title,
                area_id=candidate.area_id,
                mission_type=candidate.mission_type,
                status=MissionStatus.DRAFT,
                goal_description=candidate.goal_description,
                target_count=candidate.target_count,
                progress_count=0,
                category=candidate.category,
                reward_json=candidate.reward,
                ai_reason=candidate.ai_reason,
                linked_issue_ids_json=[
                    str(issue_id) for issue_id in candidate.linked_issue_ids
                ],
                model_used=self.generator.model_name,
                raw_response_json=raw_response,
                expires_at=now + timedelta(days=candidate.expires_in_days),
                published_at=None,
                completed_at=None,
            )
            self.repository.add(mission)
            created.append(mission)

        self.repository.flush()
        hydrated = [
            self.repository.get_detail(mission.id) or mission
            for mission in created
        ]
        return MissionGenerationResponse(
            model_used=self.generator.model_name,
            created_drafts=[mission_detail(mission) for mission in hydrated],
        )
