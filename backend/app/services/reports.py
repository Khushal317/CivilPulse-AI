from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueStatus, UpdateActorType
from app.models.issue import Issue
from app.models.issue_draft import IssueDraft
from app.models.issue_update import IssueUpdate
from app.repositories.reports import ReportRepository
from app.schemas.issues import (
    AIAnalysis,
    AIReportInput,
    PublishedReportResponse,
    ReportAnalysisInput,
    ReportDraftResponse,
    ReportDraftUpdate,
)
from app.services.ai import CivicIssueAnalyzer
from app.services.images import ValidatedImage
from app.services.storage import ImageStorage


def now_utc() -> datetime:
    return datetime.now(UTC)


def image_url(key: str) -> str:
    return f"/api/v1/media/{key}"


def draft_to_response(draft: IssueDraft) -> ReportDraftResponse:
    required = {
        "title": draft.title,
        "ai_summary": draft.ai_summary,
        "category": draft.category,
        "severity": draft.severity,
        "urgency_level": draft.urgency_level,
        "urgency_reason": draft.urgency_reason,
        "suggested_department": draft.suggested_department,
        "safety_risk": draft.safety_risk,
        "citizen_explanation": draft.citizen_explanation,
        "suggested_next_action": draft.suggested_next_action,
    }
    if any(value is None for value in required.values()):
        raise AppError(
            code="draft_incomplete",
            message="The report analysis is incomplete. Please run the analysis again.",
            status_code=409,
        )
    analysis = AIAnalysis.model_validate(required)

    return ReportDraftResponse(
        id=draft.id,
        title=analysis.title,
        ai_summary=analysis.ai_summary,
        category=analysis.category,
        severity=analysis.severity,
        urgency_level=analysis.urgency_level,
        urgency_reason=analysis.urgency_reason,
        suggested_department=analysis.suggested_department,
        safety_risk=analysis.safety_risk,
        citizen_explanation=analysis.citizen_explanation,
        suggested_next_action=analysis.suggested_next_action,
        original_description=draft.original_description,
        location=draft.location,
        landmark=draft.landmark,
        urgency_note=draft.urgency_note,
        image_url=image_url(draft.image_key),
        expires_at=draft.expires_at,
        created_at=draft.created_at,
    )


@dataclass(slots=True)
class ReportService:
    repository: ReportRepository
    storage: ImageStorage
    analyzer: CivicIssueAnalyzer
    settings: Settings

    def analyze(
        self,
        report: ReportAnalysisInput,
        image: ValidatedImage,
    ) -> ReportDraftResponse:
        stored = self.storage.save(image.data, image.mime_type, image.extension)
        try:
            ai_input = AIReportInput(
                original_description=report.original_description,
                location=report.location,
                landmark=report.landmark,
                preferred_category=report.preferred_category,
                urgency_note=report.urgency_note,
            )
            analysis = self.analyzer.analyze(ai_input, image.data, image.mime_type)
            draft = IssueDraft(
                original_description=report.original_description,
                location=report.location,
                landmark=report.landmark,
                citizen_name=report.citizen_name,
                citizen_contact=report.citizen_contact,
                urgency_note=report.urgency_note,
                image_key=stored.key,
                image_mime=stored.mime_type,
                **analysis.model_dump(),
                ai_model=self.analyzer.model_name,
                prompt_version=self.settings.ai_prompt_version,
                expires_at=now_utc() + timedelta(minutes=self.settings.report_draft_ttl_minutes),
            )
            self.repository.add_draft(draft)
            return draft_to_response(draft)
        except Exception:
            self.storage.delete(stored.key)
            raise

    def get_draft(self, draft_id: UUID) -> ReportDraftResponse:
        draft = self._active_draft(draft_id)
        return draft_to_response(draft)

    def update_draft(
        self,
        draft_id: UUID,
        changes: ReportDraftUpdate,
    ) -> ReportDraftResponse:
        draft = self._active_draft(draft_id, for_update=True)
        for field, value in changes.model_dump(exclude_unset=True).items():
            setattr(draft, field, value)
        self.repository.flush()
        return draft_to_response(draft)

    def publish(self, draft_id: UUID) -> PublishedReportResponse:
        draft = self._draft_or_404(draft_id, for_update=True)
        if draft.published_at is not None:
            existing = self.repository.find_issue_by_image_key(draft.image_key)
            if existing is None:
                raise AppError(
                    code="published_issue_missing",
                    message="The published report could not be found.",
                    status_code=409,
                )
            return self._published_response(existing, draft.published_at)

        self._ensure_not_expired(draft)
        analysis = AIAnalysis.model_validate(
            {
                "title": draft.title,
                "ai_summary": draft.ai_summary,
                "category": draft.category,
                "severity": draft.severity,
                "urgency_level": draft.urgency_level,
                "urgency_reason": draft.urgency_reason,
                "suggested_department": draft.suggested_department,
                "safety_risk": draft.safety_risk,
                "citizen_explanation": draft.citizen_explanation,
                "suggested_next_action": draft.suggested_next_action,
            },
        )
        published_at = now_utc()
        issue = Issue(
            public_reference=self._public_reference(draft.id, published_at),
            original_description=draft.original_description,
            location=draft.location,
            landmark=draft.landmark,
            image_key=draft.image_key,
            image_mime=draft.image_mime,
            status=IssueStatus.REPORTED,
            citizen_name=draft.citizen_name,
            citizen_contact=draft.citizen_contact,
            ai_model=draft.ai_model or self.analyzer.model_name,
            prompt_version=draft.prompt_version or self.settings.ai_prompt_version,
            **analysis.model_dump(),
        )
        issue.updates.append(
            IssueUpdate(
                from_status=None,
                to_status=IssueStatus.REPORTED,
                note="Issue published by a citizen.",
                actor_type=UpdateActorType.SYSTEM,
            ),
        )
        self.repository.add_issue(issue)
        draft.published_at = published_at
        self.repository.flush()
        return self._published_response(issue, published_at)

    def cancel(self, draft_id: UUID) -> None:
        draft = self._draft_or_404(draft_id, for_update=True)
        if draft.published_at is not None:
            raise AppError(
                code="draft_already_published",
                message="A published report cannot be cancelled.",
                status_code=409,
            )
        self.storage.delete(draft.image_key)
        self.repository.delete_draft(draft)

    def _active_draft(self, draft_id: UUID, *, for_update: bool = False) -> IssueDraft:
        draft = self._draft_or_404(draft_id, for_update=for_update)
        if draft.published_at is not None:
            raise AppError(
                code="draft_already_published",
                message="This report has already been published.",
                status_code=409,
            )
        self._ensure_not_expired(draft)
        return draft

    def _draft_or_404(self, draft_id: UUID, *, for_update: bool = False) -> IssueDraft:
        draft = self.repository.get_draft(draft_id, for_update=for_update)
        if draft is None:
            raise AppError(
                code="draft_not_found",
                message="The report draft was not found.",
                status_code=404,
            )
        return draft

    @staticmethod
    def _ensure_not_expired(draft: IssueDraft) -> None:
        if draft.expires_at <= now_utc():
            raise AppError(
                code="draft_expired",
                message="This report draft has expired. Please analyze the report again.",
                status_code=410,
            )

    @staticmethod
    def _public_reference(draft_id: UUID, published_at: datetime) -> str:
        return f"CP-{published_at:%Y%m%d}-{str(draft_id).replace('-', '')[:8].upper()}"

    @staticmethod
    def _published_response(issue: Issue, published_at: datetime) -> PublishedReportResponse:
        return PublishedReportResponse(
            issue_id=issue.id,
            public_reference=issue.public_reference,
            status=issue.status,
            published_at=published_at,
        )
