from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.domain.enums import IssueCategory
from app.domain.missions import MissionStatus, MissionType
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


class MissionListResponse(APIModel):
    items: list[MissionSummary]
