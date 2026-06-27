from dataclasses import dataclass
from uuid import UUID

from app.core.errors import AppError
from app.models.area import Area
from app.models.mission import Mission
from app.repositories.missions import MissionRepository
from app.schemas.missions import (
    MissionAreaSummary,
    MissionDetail,
    MissionListResponse,
    MissionSummary,
)


def area_summary(area: Area) -> MissionAreaSummary:
    return MissionAreaSummary(
        id=area.id,
        name=area.name,
        slug=area.slug,
        city=area.city,
    )


def linked_issue_ids(mission: Mission) -> list[UUID]:
    values: list[UUID] = []
    for raw_value in mission.linked_issue_ids_json:
        try:
            values.append(UUID(str(raw_value)))
        except ValueError:
            continue
    return values


def mission_summary(mission: Mission) -> MissionSummary:
    return MissionSummary(
        id=mission.id,
        title=mission.title,
        mission_type=mission.mission_type,
        status=mission.status,
        area=area_summary(mission.area),
        goal_description=mission.goal_description,
        target_count=mission.target_count,
        progress_count=mission.progress_count,
        category=mission.category,
        reward=mission.reward_json,
        ai_reason=mission.ai_reason,
        expires_at=mission.expires_at,
        published_at=mission.published_at,
        completed_at=mission.completed_at,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


def mission_detail(mission: Mission) -> MissionDetail:
    return MissionDetail(
        **mission_summary(mission).model_dump(),
        linked_issue_ids=linked_issue_ids(mission),
    )


@dataclass(slots=True)
class MissionService:
    repository: MissionRepository

    def list_public(self) -> MissionListResponse:
        return MissionListResponse(
            items=[mission_summary(mission) for mission in self.repository.list_public()],
        )

    def get_public_detail(self, mission_id: UUID) -> MissionDetail:
        mission = self.repository.get_public_detail(mission_id)
        if mission is None:
            raise AppError(
                code="mission_not_found",
                message="The community mission was not found.",
                status_code=404,
            )
        return mission_detail(mission)
