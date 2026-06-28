from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.domain.areas import AreaScoreKey
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.common import APIModel


class AreaScoreBreakdown(APIModel):
    overall: int = Field(ge=0, le=100)
    infrastructure: int = Field(ge=0, le=100)
    cleanliness: int = Field(ge=0, le=100)
    safety: int = Field(ge=0, le=100)
    participation: int = Field(ge=0, le=100)
    responsiveness: int = Field(ge=0, le=100)
    environment: int = Field(ge=0, le=100)


class AreaCivicGenomeProfile(APIModel):
    civic_health_score: int = Field(ge=0, le=100)
    community_power_score: int = Field(ge=0, le=100)
    confidence_level: Literal["low", "medium", "high"]
    confidence_reason: str
    score_limit_reasons: list[str] = Field(default_factory=list)


class AreaSummary(APIModel):
    id: UUID
    name: str
    slug: str
    city: str
    rank: int | None
    status_label: str
    scores: AreaScoreBreakdown
    civic_genome: AreaCivicGenomeProfile
    open_issues: int = Field(ge=0)
    resolved_this_week: int = Field(ge=0)
    active_missions: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class AreaListResponse(APIModel):
    items: list[AreaSummary]


class AreaScoreEventResponse(APIModel):
    id: UUID
    event_type: str
    related_issue_id: UUID | None
    related_mission_id: UUID | None
    score_key: AreaScoreKey
    score_change: int
    previous_score: int = Field(ge=0, le=100)
    new_score: int = Field(ge=0, le=100)
    reason: str
    created_at: datetime


class AreaActiveIssueResponse(APIModel):
    id: UUID
    public_reference: str
    title: str
    category: IssueCategory
    severity: IssueSeverity
    status: IssueStatus
    location: str
    landmark: str | None
    updated_at: datetime


class AreaInsightResponse(APIModel):
    explanation: str
    next_best_actions: list[str] = Field(default_factory=list, min_length=1, max_length=5)
    model_used: str


class AreaDetail(AreaSummary):
    total_issues: int = Field(ge=0)
    recent_score_events: list[AreaScoreEventResponse] = Field(default_factory=list)
    active_issues: list[AreaActiveIssueResponse] = Field(default_factory=list)
    insight: AreaInsightResponse
