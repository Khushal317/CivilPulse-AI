from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, UrgencyLevel
from app.schemas.issues import AIAnalysis, AIReportInput

SYSTEM_INSTRUCTION = """
You are CivicPulse AI, a civic issue triage assistant. Convert citizen-provided text and
one issue photograph into a concise, neutral, trackable civic complaint.

Rules:
- Do not claim that a government department has accepted or verified the issue.
- Do not identify people or infer sensitive personal traits.
- Use only the supported category, severity, and urgency enum values.
- Treat the citizen's location and urgency claims as unverified context.
- Write clear civic language without exaggeration.
- If the image and text conflict, describe the uncertainty in safety_risk or citizen_explanation.
- Critical severity is reserved for credible immediate threats to life, electrical danger,
  structural collapse, severe contamination, or similarly acute hazards.
""".strip()


class CivicIssueAnalyzer(Protocol):
    model_name: str

    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis: ...


class DemoCivicIssueAnalyzer:
    model_name = "demo-civic-analyzer-v1"

    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis:
        del image_bytes, image_mime
        text = f"{report.original_description} {report.urgency_note or ''}".lower()
        if any(word in text for word in ("pothole", "road", "footpath")):
            category = IssueCategory.ROAD_DAMAGE
            department = "Public Works / Road Maintenance"
        elif any(word in text for word in ("garbage", "waste", "dumping")):
            category = IssueCategory.GARBAGE_WASTE
            department = "Sanitation Department"
        elif any(word in text for word in ("streetlight", "light", "electrical")):
            category = IssueCategory.STREETLIGHT
            department = "Municipal Lighting"
        elif any(word in text for word in ("water", "leak")):
            category = IssueCategory.WATER_LEAKAGE
            department = "Water Department"
        elif any(word in text for word in ("drain", "sewage", "sewer")):
            category = IssueCategory.DRAINAGE_SEWAGE
            department = "Drainage / Sewage Department"
        else:
            category = report.preferred_category or IssueCategory.OTHER
            department = "Municipal Citizen Services"

        elevated = any(word in text for word in ("school", "hospital", "danger", "unsafe", "kids"))
        severity = IssueSeverity.HIGH if elevated else IssueSeverity.MEDIUM
        urgency = UrgencyLevel.URGENT if elevated else UrgencyLevel.SOON
        short_location = report.landmark or report.location

        return AIAnalysis(
            title=f"{category.value.replace('_', ' ').title()} near {short_location}"[:180],
            ai_summary=(
                f"A citizen reported {report.original_description.strip()} "
                f"at {report.location}. Inspection by the responsible civic team is recommended."
            ),
            category=category,
            severity=severity,
            urgency_level=urgency,
            urgency_reason=(
                "The report describes a possible public safety risk in a sensitive area."
                if elevated
                else "The issue may worsen or disrupt local residents if left unattended."
            ),
            suggested_department=department,
            safety_risk=(
                "Residents should use caution near the reported location until it is inspected."
            ),
            citizen_explanation=(
                "Your report has been converted into a structured civic complaint. "
                "Review the details before publishing it."
            ),
            suggested_next_action="Publish the report so the community can verify and track it.",
        )


class GeminiCivicIssueAnalyzer:
    def __init__(self, settings: Settings) -> None:
        assert settings.gemini_api_key is not None
        self.model_name = settings.gemini_model
        self._prompt_version = settings.ai_prompt_version
        self._max_attempts = settings.gemini_max_attempts
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1_000),
        )

    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis:
        prompt = (
            f"Prompt version: {self._prompt_version}\n"
            f"Citizen description: {report.original_description}\n"
            f"Location/area: {report.location}\n"
            f"Landmark: {report.landmark or 'Not provided'}\n"
            f"Citizen urgency note: {report.urgency_note or 'Not provided'}\n"
            f"Citizen-selected category: "
            f"{report.preferred_category.value if report.preferred_category else 'Not selected'}\n"
            "Analyze the text and image and return the required structured complaint."
        )

        last_error: Exception | None = None
        for _attempt in range(self._max_attempts):
            try:
                contents = types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                        types.Part.from_bytes(data=image_bytes, mime_type=image_mime),
                    ],
                )
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=AIAnalysis,
                        temperature=0.1,
                    ),
                )
                if isinstance(response.parsed, AIAnalysis):
                    return response.parsed
                if response.text:
                    return AIAnalysis.model_validate_json(response.text)
                raise ValueError("Gemini returned no structured content")
            except (ValidationError, ValueError) as exc:
                last_error = exc
                continue
            except Exception as exc:
                raise AppError(
                    code="ai_unavailable",
                    message=(
                        "CivicPulse AI could not analyze the report right now. Please try again."
                    ),
                    status_code=503,
                ) from exc

        raise AppError(
            code="ai_invalid_response",
            message="The AI response could not be validated. Please try the analysis again.",
            status_code=502,
        ) from last_error


@lru_cache
def get_civic_issue_analyzer() -> CivicIssueAnalyzer:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        return GeminiCivicIssueAnalyzer(settings)
    return DemoCivicIssueAnalyzer()
