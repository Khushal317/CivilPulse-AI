from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UpdateActorType,
    UrgencyLevel,
)
from app.schemas.common import APIModel


class IssueDraftCreate(APIModel):
    original_description: str = Field(min_length=10, max_length=4_000)
    location: str = Field(min_length=2, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)
    citizen_name: str | None = Field(default=None, max_length=120)
    citizen_contact: str | None = Field(default=None, max_length=255)
    urgency_note: str | None = Field(default=None, max_length=1_000)
    image_key: str = Field(min_length=1, max_length=512)


class ReportAnalysisInput(APIModel):
    original_description: str = Field(min_length=10, max_length=4_000)
    location: str = Field(min_length=2, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)
    preferred_category: IssueCategory | None = None
    citizen_name: str | None = Field(default=None, max_length=120)
    citizen_contact: str | None = Field(default=None, max_length=255)
    urgency_note: str | None = Field(default=None, max_length=1_000)


class AIReportInput(APIModel):
    original_description: str
    location: str
    landmark: str | None
    preferred_category: IssueCategory | None
    urgency_note: str | None


class AIAnalysis(APIModel):
    title: str = Field(min_length=5, max_length=180)
    ai_summary: str = Field(min_length=20, max_length=4_000)
    category: IssueCategory
    severity: IssueSeverity
    urgency_level: UrgencyLevel
    urgency_reason: str = Field(min_length=10, max_length=2_000)
    suggested_department: str = Field(min_length=2, max_length=180)
    safety_risk: str = Field(min_length=5, max_length=2_000)
    citizen_explanation: str = Field(min_length=5, max_length=2_000)
    suggested_next_action: str = Field(min_length=5, max_length=2_000)


class ReportDraftUpdate(APIModel):
    title: str | None = Field(default=None, min_length=5, max_length=180)
    ai_summary: str | None = Field(default=None, min_length=20, max_length=4_000)
    category: IssueCategory | None = None
    severity: IssueSeverity | None = None
    urgency_level: UrgencyLevel | None = None
    urgency_reason: str | None = Field(default=None, min_length=10, max_length=2_000)
    suggested_department: str | None = Field(default=None, min_length=2, max_length=180)
    safety_risk: str | None = Field(default=None, min_length=5, max_length=2_000)
    citizen_explanation: str | None = Field(default=None, min_length=5, max_length=2_000)
    suggested_next_action: str | None = Field(default=None, min_length=5, max_length=2_000)
    original_description: str | None = Field(default=None, min_length=10, max_length=4_000)
    location: str | None = Field(default=None, min_length=2, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def prevent_null_required_fields(self) -> "ReportDraftUpdate":
        nullable_fields = {"landmark"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ReportDraftResponse(AIAnalysis):
    id: UUID
    original_description: str
    location: str
    landmark: str | None
    urgency_note: str | None
    image_url: str
    expires_at: datetime
    created_at: datetime


class PublishedReportResponse(APIModel):
    issue_id: UUID
    public_reference: str
    status: IssueStatus
    published_at: datetime


class IssueUpdatePublic(APIModel):
    id: UUID
    from_status: IssueStatus | None
    to_status: IssueStatus
    note: str | None
    actor_type: UpdateActorType
    created_at: datetime


class CommunityCounts(APIModel):
    saw_this_too: int = Field(default=0, ge=0)
    still_unresolved: int = Field(default=0, ge=0)
    fixed: int = Field(default=0, ge=0)
    incorrect: int = Field(default=0, ge=0)


class IssueListItem(APIModel):
    id: UUID
    public_reference: str
    title: str
    category: IssueCategory
    severity: IssueSeverity
    location: str
    landmark: str | None
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    verification_count: int = Field(default=0, ge=0)


class IssuePublicDetail(IssueListItem):
    original_description: str
    ai_summary: str
    urgency_level: UrgencyLevel
    urgency_reason: str
    suggested_department: str
    safety_risk: str
    citizen_explanation: str
    suggested_next_action: str
    image_url: str
    community_counts: CommunityCounts
    updates: list[IssueUpdatePublic]


class IssueAdminDetail(IssuePublicDetail):
    citizen_name: str | None
    citizen_contact: str | None
    image_key: str
    ai_model: str
    prompt_version: str


class CommunityActionCreate(APIModel):
    action_type: CommunityActionType
