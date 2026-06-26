from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.common import APIModel

RiskLevel = Literal["low", "medium", "high", "critical"]


class OperationsModel(APIModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        str_strip_whitespace=True,
    )


class OperationsIssueInput(OperationsModel):
    issue_id: UUID
    public_reference: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=180)
    category: IssueCategory
    department: str = Field(min_length=1, max_length=180)
    severity: IssueSeverity
    status: IssueStatus
    location: str = Field(min_length=1, max_length=255)
    landmark: str | None = Field(default=None, max_length=255)
    verification_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    fixed_count: int = Field(ge=0)
    incorrect_count: int = Field(ge=0)
    created_at: datetime
    age_hours: int = Field(ge=0)
    age_days: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=4_000)
    latest_admin_update: str | None = Field(default=None, max_length=2_000)


class UrgentIssueRecommendation(OperationsModel):
    issue_id: UUID
    public_reference: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=180)
    location: str = Field(min_length=1, max_length=320)
    department: str = Field(min_length=1, max_length=180)
    severity: IssueSeverity
    priority_reason: str = Field(min_length=5, max_length=2_000)
    recommended_action: str = Field(min_length=5, max_length=2_000)
    suggested_time_window: str = Field(min_length=2, max_length=120)


class DuplicateIssueReference(OperationsModel):
    issue_id: UUID
    public_reference: str = Field(min_length=1, max_length=24)
    title: str = Field(min_length=1, max_length=180)


class DuplicateCluster(OperationsModel):
    cluster_title: str = Field(min_length=5, max_length=180)
    issues: list[DuplicateIssueReference] = Field(min_length=2, max_length=10)
    reason: str = Field(min_length=5, max_length=2_000)
    recommended_action: str = Field(min_length=5, max_length=2_000)


class AreaHotspot(OperationsModel):
    area: str = Field(min_length=1, max_length=255)
    issue_count: int = Field(ge=1)
    main_categories: list[IssueCategory] = Field(min_length=1, max_length=5)
    risk_level: RiskLevel
    insight: str = Field(min_length=5, max_length=2_000)


class DepartmentPriority(OperationsModel):
    department: str = Field(min_length=1, max_length=180)
    open_issues: int = Field(ge=1)
    high_priority_count: int = Field(ge=0)
    recommended_focus: str = Field(min_length=5, max_length=2_000)


class EscalationMessage(OperationsModel):
    department: str = Field(min_length=1, max_length=180)
    issue_id: UUID
    public_reference: str = Field(min_length=1, max_length=24)
    issue_title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=10, max_length=2_000)


class PredictedRisk(OperationsModel):
    issue_id: UUID
    public_reference: str = Field(min_length=1, max_length=24)
    issue_title: str = Field(min_length=1, max_length=180)
    risk: str = Field(min_length=5, max_length=2_000)
    risk_level: RiskLevel
    preventive_action: str = Field(min_length=5, max_length=2_000)


class OperationsAnalysis(OperationsModel):
    total_issues_analyzed: int = Field(ge=0)
    model_used: str = Field(min_length=1, max_length=120)
    executive_summary: str = Field(min_length=5, max_length=4_000)
    urgent_issues: list[UrgentIssueRecommendation] = Field(default_factory=list, max_length=5)
    duplicate_clusters: list[DuplicateCluster] = Field(default_factory=list, max_length=10)
    area_hotspots: list[AreaHotspot] = Field(default_factory=list, max_length=10)
    department_priorities: list[DepartmentPriority] = Field(default_factory=list, max_length=10)
    escalation_messages: list[EscalationMessage] = Field(default_factory=list, max_length=10)
    predicted_risks: list[PredictedRisk] = Field(default_factory=list, max_length=10)
    raw_response: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def empty_report_has_empty_sections(self) -> "OperationsAnalysis":
        populated_sections = (
            self.urgent_issues
            or self.duplicate_clusters
            or self.area_hotspots
            or self.department_priorities
            or self.escalation_messages
            or self.predicted_risks
        )
        if self.total_issues_analyzed == 0:
            if populated_sections:
                raise ValueError("empty operations reports cannot contain issue sections")
        elif not populated_sections:
            raise ValueError("operations reports with active issues require at least one section")
        return self


class GeminiOperationsPayload(OperationsModel):
    executive_summary: str = Field(min_length=5, max_length=4_000)
    urgent_issues: list[UrgentIssueRecommendation] = Field(default_factory=list, max_length=5)
    duplicate_clusters: list[DuplicateCluster] = Field(default_factory=list, max_length=10)
    area_hotspots: list[AreaHotspot] = Field(default_factory=list, max_length=10)
    department_priorities: list[DepartmentPriority] = Field(default_factory=list, max_length=10)
    escalation_messages: list[EscalationMessage] = Field(default_factory=list, max_length=10)
    predicted_risks: list[PredictedRisk] = Field(default_factory=list, max_length=10)


class OperationsReportResponse(OperationsAnalysis):
    id: UUID
    generated_at: datetime
    created_at: datetime
