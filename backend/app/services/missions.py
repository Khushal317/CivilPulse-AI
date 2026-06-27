from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import AppError
from app.domain.enums import CommunityActionType
from app.domain.missions import MissionActionType, MissionStatus
from app.models.area import Area
from app.models.mission import Mission
from app.repositories.missions import MissionRepository
from app.schemas.missions import (
    AdminMissionListResponse,
    MissionActionResponse,
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


def joined_count(mission: Mission) -> int:
    return sum(
        1
        for action in mission.actions
        if action.action_type is MissionActionType.JOINED
    )


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
        joined_count=joined_count(mission),
        expires_at=mission.expires_at,
        published_at=mission.published_at,
        completed_at=mission.completed_at,
        created_at=mission.created_at,
        updated_at=mission.updated_at,
    )


def mission_detail(
    mission: Mission,
    *,
    viewer_actions: list[MissionActionType] | None = None,
) -> MissionDetail:
    return MissionDetail(
        **mission_summary(mission).model_dump(),
        linked_issue_ids=linked_issue_ids(mission),
        viewer_actions=viewer_actions or [],
    )


def now_utc() -> datetime:
    return datetime.now(UTC)


def aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@dataclass(slots=True)
class MissionService:
    repository: MissionRepository

    def list_admin(self) -> AdminMissionListResponse:
        drafts: list[MissionDetail] = []
        active: list[MissionDetail] = []
        completed: list[MissionDetail] = []
        expired: list[MissionDetail] = []
        for mission in self.repository.list_admin():
            detail = mission_detail(mission)
            if mission.status is MissionStatus.DRAFT:
                drafts.append(detail)
            elif mission.status is MissionStatus.ACTIVE:
                active.append(detail)
            elif mission.status is MissionStatus.COMPLETED:
                completed.append(detail)
            elif mission.status is MissionStatus.EXPIRED:
                expired.append(detail)
        return AdminMissionListResponse(
            drafts=drafts,
            active=active,
            completed=completed,
            expired=expired,
        )

    def list_public(self) -> MissionListResponse:
        return MissionListResponse(
            items=[mission_summary(mission) for mission in self.repository.list_public()],
        )

    def publish(self, mission_id: UUID) -> MissionDetail:
        mission = self._require_mission(mission_id)
        if mission.status is not MissionStatus.DRAFT:
            raise AppError(
                code="mission_not_publishable",
                message="Only draft missions can be published.",
                status_code=409,
            )
        now = now_utc()
        mission.status = MissionStatus.ACTIVE
        mission.published_at = now
        mission.completed_at = None
        self.repository.flush()
        return mission_detail(mission)

    def expire(self, mission_id: UUID) -> MissionDetail:
        mission = self._require_mission(mission_id)
        if mission.status is not MissionStatus.ACTIVE:
            raise AppError(
                code="mission_not_expirable",
                message="Only active missions can be expired.",
                status_code=409,
            )
        now = now_utc()
        mission.status = MissionStatus.EXPIRED
        if mission.expires_at is None or aware_datetime(mission.expires_at) > now:
            mission.expires_at = now
        mission.completed_at = None
        self.repository.flush()
        return mission_detail(mission)

    def complete(self, mission_id: UUID) -> MissionDetail:
        mission = self._require_mission(mission_id)
        if mission.status is not MissionStatus.ACTIVE:
            raise AppError(
                code="mission_not_completable",
                message="Only active missions can be manually completed.",
                status_code=409,
            )
        mission.status = MissionStatus.COMPLETED
        mission.progress_count = mission.target_count
        mission.completed_at = now_utc()
        self.repository.flush()
        return mission_detail(mission)

    def get_public_detail(self, mission_id: UUID, actor_hash: str | None = None) -> MissionDetail:
        mission = self.repository.get_public_detail(mission_id)
        if mission is None:
            raise AppError(
                code="mission_not_found",
                message="The community mission was not found.",
                status_code=404,
            )
        return mission_detail(
            mission,
            viewer_actions=self.repository.viewer_actions(mission.id, actor_hash)
            if actor_hash
            else [],
        )

    def submit_action(
        self,
        mission_id: UUID,
        action_type: MissionActionType,
        actor_hash: str,
        *,
        issue_id: UUID | None = None,
    ) -> MissionActionResponse:
        mission = self.repository.get_detail(mission_id)
        if mission is None:
            raise AppError(
                code="mission_not_found",
                message="The community mission was not found.",
                status_code=404,
            )
        if mission.status is not MissionStatus.ACTIVE:
            code = (
                "mission_completed"
                if mission.status is MissionStatus.COMPLETED
                else "mission_expired"
                if mission.status is MissionStatus.EXPIRED
                else "mission_unavailable"
            )
            raise AppError(
                code=code,
                message="This mission is not accepting public actions.",
                status_code=409,
            )

        normalized_issue_id = self._validate_action_issue(mission, action_type, issue_id)
        accepted = self.repository.add_action_if_absent(
            mission.id,
            action_type,
            actor_hash,
            issue_id=normalized_issue_id,
        )
        if accepted:
            self._record_linked_issue_signal(action_type, actor_hash, normalized_issue_id)
            if mission.progress_count < mission.target_count:
                mission.progress_count += 1
            self.repository.flush()

        return MissionActionResponse(
            action_type=action_type,
            accepted=accepted,
            mission_status=mission.status,
            progress_count=mission.progress_count,
            target_count=mission.target_count,
            joined_count=self.repository.action_counts(mission.id).get(
                MissionActionType.JOINED,
                0,
            ),
            viewer_actions=self.repository.viewer_actions(mission.id, actor_hash),
        )

    def _validate_action_issue(
        self,
        mission: Mission,
        action_type: MissionActionType,
        issue_id: UUID | None,
    ) -> UUID | None:
        issue_linked_actions = {
            MissionActionType.VERIFIED_ISSUE,
            MissionActionType.CONFIRMED_UNRESOLVED,
            MissionActionType.CONFIRMED_FIXED,
        }
        if action_type in issue_linked_actions:
            if issue_id is None:
                raise AppError(
                    code="mission_issue_required",
                    message="This mission action requires a linked issue.",
                    status_code=422,
                )
            if issue_id not in linked_issue_ids(mission):
                raise AppError(
                    code="mission_issue_not_linked",
                    message="This issue is not linked to the mission.",
                    status_code=409,
                )
            return issue_id
        if issue_id is not None:
            raise AppError(
                code="mission_issue_not_allowed",
                message="This mission action does not use a linked issue.",
                status_code=422,
            )
        return None

    def _record_linked_issue_signal(
        self,
        action_type: MissionActionType,
        actor_hash: str,
        issue_id: UUID | None,
    ) -> None:
        if issue_id is None:
            return
        mapping = {
            MissionActionType.VERIFIED_ISSUE: CommunityActionType.SAW_THIS_TOO,
            MissionActionType.CONFIRMED_UNRESOLVED: CommunityActionType.STILL_UNRESOLVED,
            MissionActionType.CONFIRMED_FIXED: CommunityActionType.FIXED,
        }
        community_action = mapping.get(action_type)
        if community_action is not None:
            self.repository.add_community_action_if_absent(
                issue_id,
                community_action,
                actor_hash,
            )

    def _require_mission(self, mission_id: UUID) -> Mission:
        mission = self.repository.get_detail(mission_id)
        if mission is None:
            raise AppError(
                code="mission_not_found",
                message="The community mission was not found.",
                status_code=404,
            )
        return mission
