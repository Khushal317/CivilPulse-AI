from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from app.domain.areas import AreaScoreKey
from app.domain.enums import IssueCategory
from app.domain.missions import MissionActionType, MissionStatus, MissionType
from app.schemas.common import APIModel


class MissionAreaSummary(APIModel):
    id: UUID
    name: str
    slug: str
    city: str


class MissionSummary(APIModel):
    id: UUID
    title: str
    mission_type: MissionType
    status: MissionStatus
    area: MissionAreaSummary
    goal_description: str
    target_count: int = Field(gt=0)
    progress_count: int = Field(ge=0)
    category: IssueCategory | None
    reward: dict[str, Any] = Field(default_factory=dict)
    ai_reason: str
    joined_count: int = Field(default=0, ge=0)
    expires_at: datetime | None
    published_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_lifecycle_fields(self) -> "MissionSummary":
        if self.progress_count > self.target_count:
            raise ValueError("Mission progress cannot exceed the target count.")
        published_statuses = {
            MissionStatus.ACTIVE,
            MissionStatus.COMPLETED,
            MissionStatus.EXPIRED,
        }
        if self.status in published_statuses and self.published_at is None:
            raise ValueError("Published missions must include published_at.")
        if self.status is MissionStatus.COMPLETED and self.completed_at is None:
            raise ValueError("Completed missions must include completed_at.")
        return self


class MissionDetail(MissionSummary):
    linked_issue_ids: list[UUID] = Field(default_factory=list)
    viewer_actions: list[MissionActionType] = Field(default_factory=list)


class MissionListResponse(APIModel):
    items: list[MissionSummary]


class MissionActionCreate(APIModel):
    action_type: MissionActionType
    issue_id: UUID | None = None


class MissionActionResponse(APIModel):
    action_type: MissionActionType
    accepted: bool
    mission_status: MissionStatus
    progress_count: int = Field(ge=0)
    target_count: int = Field(gt=0)
    joined_count: int = Field(ge=0)
    viewer_actions: list[MissionActionType]


class AdminMissionListResponse(APIModel):
    drafts: list[MissionDetail]
    active: list[MissionDetail]
    completed: list[MissionDetail]
    expired: list[MissionDetail]


class ManualMissionDraft(APIModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=8, max_length=180)
    area_id: UUID
    mission_type: MissionType
    goal_description: str = Field(min_length=20, max_length=700)
    target_count: int = Field(ge=1, le=500)
    category: IssueCategory | None = None
    reward_points: int = Field(default=20, ge=0, le=100)
    reward_score_key: AreaScoreKey = AreaScoreKey.PARTICIPATION
    ai_reason: str = Field(min_length=20, max_length=900)
    linked_issue_ids: list[UUID] = Field(default_factory=list, max_length=10)
    expires_in_days: int = Field(default=7, ge=1, le=30)

    @model_validator(mode="after")
    def validate_reward_score_key(self) -> "ManualMissionDraft":
        if self.reward_score_key is AreaScoreKey.OVERALL:
            raise ValueError("Manual mission rewards must target a component score.")
        return self


class ManualMissionCreate(ManualMissionDraft):
    publish: bool = False


class GeneratedMissionCandidate(APIModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=8, max_length=180)
    area_id: UUID
    mission_type: MissionType
    goal_description: str = Field(min_length=20, max_length=700)
    target_count: int = Field(ge=1, le=500)
    category: IssueCategory | None = None
    reward: dict[str, Any] = Field(default_factory=dict)
    ai_reason: str = Field(min_length=20, max_length=900)
    linked_issue_ids: list[UUID] = Field(default_factory=list, max_length=10)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class MissionGenerationPayload(APIModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    missions: list[GeneratedMissionCandidate] = Field(min_length=1, max_length=5)


class MissionGenerationResponse(APIModel):
    model_used: str
    created_drafts: list[MissionDetail]
