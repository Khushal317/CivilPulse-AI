from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.common import APIModel
from app.schemas.issues import CommunityCounts, IssueUpdatePublic


class AdminLoginRequest(APIModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class AdminSessionResponse(APIModel):
    username: str
    expires_at: datetime
    csrf_token: str


class AdminDashboardMetrics(APIModel):
    total_reports: int = Field(ge=0)
    high_severity: int = Field(ge=0)
    verified: int = Field(ge=0)
    pending: int = Field(ge=0)
    resolved: int = Field(ge=0)


class CategoryMetric(APIModel):
    category: IssueCategory
    count: int = Field(ge=0)


class AdminIssueSummary(APIModel):
    id: UUID
    public_reference: str
    title: str
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    location: str
    landmark: str | None
    created_at: datetime
    updated_at: datetime
    verification_count: int = Field(ge=0)


class AdminDashboardResponse(APIModel):
    metrics: AdminDashboardMetrics
    category_breakdown: list[CategoryMetric]
    latest_reports: list[AdminIssueSummary]
    priority_issues: list[AdminIssueSummary]


class AdminIssueListQuery(APIModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = Field(default=None, max_length=255)
    category: IssueCategory | None = None
    severity: IssueSeverity | None = None
    status: IssueStatus | None = None


class AdminIssueListResponse(APIModel):
    items: list[AdminIssueSummary]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class AdminIssueDetail(AdminIssueSummary):
    original_description: str
    ai_summary: str
    urgency_level: str
    urgency_reason: str
    suggested_department: str
    safety_risk: str
    citizen_explanation: str
    suggested_next_action: str
    image_url: str
    image_mime: str
    citizen_name: str | None
    citizen_contact: str | None
    ai_model: str
    prompt_version: str
    community_counts: CommunityCounts
    updates: list[IssueUpdatePublic]


class AdminStatusUpdateRequest(APIModel):
    to_status: IssueStatus
    note: str | None = Field(default=None, max_length=2_000)
    rejection_reason: str | None = Field(default=None, min_length=5, max_length=2_000)

    @model_validator(mode="after")
    def require_rejection_reason(self) -> "AdminStatusUpdateRequest":
        if self.to_status is IssueStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting an issue")
        if self.to_status is not IssueStatus.REJECTED and self.rejection_reason is not None:
            raise ValueError("rejection_reason is only valid when rejecting an issue")
        return self


class DuplicateIssueResolutionRequest(APIModel):
    canonical_issue_id: UUID
    duplicate_issue_ids: list[UUID] = Field(min_length=1, max_length=20)
    reason: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def prevent_self_duplicate(self) -> "DuplicateIssueResolutionRequest":
        if self.canonical_issue_id in self.duplicate_issue_ids:
            raise ValueError("canonical_issue_id cannot also be marked as duplicate")
        if len(set(self.duplicate_issue_ids)) != len(self.duplicate_issue_ids):
            raise ValueError("duplicate_issue_ids cannot contain repeated issue IDs")
        return self


class DuplicateIssueResolutionResponse(APIModel):
    canonical_issue: AdminIssueSummary
    duplicates_marked: list[AdminIssueSummary]
