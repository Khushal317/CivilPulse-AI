import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import types

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.repositories.missions import MissionRepository
from app.schemas.missions import ManualMissionDraft

MISSION_REFINEMENT_SYSTEM_INSTRUCTION = """
You are CivicPulse AI's Community Mission Editor.

Your job:
- Improve an administrator-written community mission draft.
- Keep the mission safe, concrete, measurable, and locally actionable.
- Preserve administrator intent, selected area, category, reward, linked issues, and expiry.

Rules:
- Return valid JSON only.
- Never ask citizens to do dangerous work, enter private property, confront people, or replace
  official repair crews.
- Never include private citizen details, contacts, image identifiers, actor hashes, sessions,
  secrets, or credentials.
- Do not invent area IDs or issue IDs.
""".strip()


class CivicMissionRefiner(Protocol):
    model_name: str

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft: ...


def mission_refinement_prompt(draft: ManualMissionDraft) -> str:
    return (
        "Refine this administrator-written CivicPulse AI community mission draft and "
        "return exactly one JSON object. Do not wrap the response in markdown or code fences.\n"
        "Keep the area_id, category, reward_points, reward_score_key, linked_issue_ids, "
        "expires_in_days, and mission_type unless the text is invalid.\n\n"
        "Required JSON shape:\n"
        "{\n"
        '  "title": "clear mission title",\n'
        '  "area_id": "same UUID",\n'
        '  "mission_type": "verification|fix_confirmation|hotspot|category|volunteer",\n'
        '  "goal_description": "safe measurable mission goal",\n'
        '  "target_count": 5,\n'
        '  "category": "road_damage|null",\n'
        '  "reward_points": 20,\n'
        '  "reward_score_key": "participation",\n'
        '  "ai_reason": "why this mission is useful now",\n'
        '  "linked_issue_ids": [],\n'
        '  "expires_in_days": 7\n'
        "}\n\n"
        f"Manual mission draft JSON:\n{json.dumps(draft.model_dump(mode='json'))}"
    )


class DemoCivicMissionRefiner:
    model_name = "demo-civic-mission-refiner-v1"

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        title = draft.title.strip()
        if not title.lower().startswith(("verify", "confirm", "map", "coordinate")):
            title = f"Verify {title[0].lower()}{title[1:]}"
        return draft.model_copy(
            update={
                "title": title,
                "goal_description": (
                    f"{draft.goal_description.rstrip('.')} through safe public observation "
                    "and clear community updates."
                )[:700],
                "ai_reason": (
                    f"{draft.ai_reason.rstrip('.')} This refined mission keeps the action "
                    "measurable, safe, and ready for administrator review."
                )[:900],
            },
        )


class GeminiCivicMissionRefiner:
    def __init__(self, settings: Settings) -> None:
        assert settings.gemini_api_key is not None
        self.model_name = settings.gemini_model
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1_000),
        )

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=types.Content(
                role="user",
                parts=[types.Part.from_text(text=mission_refinement_prompt(draft))],
            ),
            config=types.GenerateContentConfig(
                system_instruction=MISSION_REFINEMENT_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        if isinstance(response.parsed, ManualMissionDraft):
            refined = response.parsed
        elif response.text:
            refined = ManualMissionDraft.model_validate_json(response.text)
        else:
            raise ValueError("Gemini returned no mission refinement content")
        return refined.model_copy(
            update={
                "area_id": draft.area_id,
                "category": draft.category,
                "reward_points": draft.reward_points,
                "reward_score_key": draft.reward_score_key,
                "linked_issue_ids": draft.linked_issue_ids,
                "expires_in_days": draft.expires_in_days,
            },
        )


class SafeFallbackMissionRefiner:
    def __init__(self, primary: CivicMissionRefiner, fallback: CivicMissionRefiner) -> None:
        self.model_name = primary.model_name
        self._primary = primary
        self._fallback = fallback

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        try:
            return self._primary.refine(draft)
        except Exception:
            return self._fallback.refine(draft)


@dataclass(slots=True)
class MissionRefinementService:
    repository: MissionRepository
    refiner: CivicMissionRefiner

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        if self.repository.get_area(draft.area_id) is None:
            raise AppError(
                code="mission_area_not_found",
                message="The selected neighborhood area was not found.",
                status_code=404,
            )
        return self.refiner.refine(draft)


@lru_cache
def get_civic_mission_refiner() -> CivicMissionRefiner:
    settings = get_settings()
    fallback = DemoCivicMissionRefiner()
    if settings.ai_provider == "gemini":
        return SafeFallbackMissionRefiner(GeminiCivicMissionRefiner(settings), fallback)
    return SafeFallbackMissionRefiner(fallback, fallback)
