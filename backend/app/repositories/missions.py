from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import CommunityActionType, IssueStatus
from app.domain.missions import MissionActionType, MissionStatus
from app.models.area import Area
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.mission import Mission
from app.models.mission_action import MissionAction

PUBLIC_DETAIL_STATUSES = {
    MissionStatus.ACTIVE,
    MissionStatus.COMPLETED,
    MissionStatus.EXPIRED,
}
MISSION_CONTEXT_ISSUE_STATUSES = {
    IssueStatus.REPORTED,
    IssueStatus.COMMUNITY_VERIFIED,
    IssueStatus.ESCALATED,
    IssueStatus.IN_PROGRESS,
}


@dataclass(frozen=True, slots=True)
class MissionAreaContext:
    id: UUID
    name: str
    slug: str
    city: str
    overall_score: int
    infrastructure_score: int
    cleanliness_score: int
    safety_score: int
    participation_score: int
    responsiveness_score: int
    environment_score: int


@dataclass(frozen=True, slots=True)
class MissionIssueContext:
    id: UUID
    public_reference: str
    title: str
    ai_summary: str
    category: str
    severity: str
    urgency_level: str
    suggested_department: str
    location: str
    landmark: str | None
    status: str
    area_id: UUID | None
    age_days: int


@dataclass(frozen=True, slots=True)
class MissionActiveContext:
    id: UUID
    title: str
    area_id: UUID
    mission_type: str
    category: str | None
    target_count: int
    progress_count: int
    expires_at: str | None


@dataclass(frozen=True, slots=True)
class MissionContext:
    areas: list[MissionAreaContext]
    active_issues: list[MissionIssueContext]
    existing_active_missions: list[MissionActiveContext]


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class MissionRepository(Protocol):
    def add(self, mission: Mission) -> Mission: ...

    def delete(self, mission: Mission) -> None: ...

    def generation_context(self, *, issue_limit: int = 50) -> MissionContext: ...

    def get_area(self, area_id: UUID) -> Area | None: ...

    def get_detail(self, mission_id: UUID) -> Mission | None: ...

    def list_admin(self) -> list[Mission]: ...

    def list_public(self) -> list[Mission]: ...

    def get_public_detail(self, mission_id: UUID) -> Mission | None: ...

    def get_active_for_action(self, mission_id: UUID) -> Mission | None: ...

    def action_counts(self, mission_id: UUID) -> dict[MissionActionType, int]: ...

    def viewer_actions(self, mission_id: UUID, actor_hash: str) -> list[MissionActionType]: ...

    def add_action_if_absent(
        self,
        mission_id: UUID,
        action_type: MissionActionType,
        actor_hash: str,
        *,
        issue_id: UUID | None,
    ) -> bool: ...

    def add_community_action_if_absent(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> bool: ...

    def flush(self) -> None: ...


class SQLAlchemyMissionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, mission: Mission) -> Mission:
        self._session.add(mission)
        self._session.flush()
        return mission

    def delete(self, mission: Mission) -> None:
        self._session.delete(mission)
        self._session.flush()

    def get_area(self, area_id: UUID) -> Area | None:
        return self._session.get(Area, area_id)

    def generation_context(self, *, issue_limit: int = 50) -> MissionContext:
        areas = list(
            self._session.scalars(
                select(Area).order_by(Area.overall_score.asc(), Area.name.asc()),
            ).all(),
        )
        issues = list(
            self._session.scalars(
                select(Issue)
                .where(Issue.status.in_(MISSION_CONTEXT_ISSUE_STATUSES))
                .options(selectinload(Issue.area))
                .order_by(Issue.severity.desc(), Issue.created_at.asc())
                .limit(issue_limit),
            ).all(),
        )
        missions = list(
            self._session.scalars(
                select(Mission)
                .where(Mission.status == MissionStatus.ACTIVE)
                .options(selectinload(Mission.area), selectinload(Mission.actions))
                .order_by(Mission.created_at.desc())
                .limit(20),
            ).all(),
        )
        now = datetime.now(UTC)
        return MissionContext(
            areas=[
                MissionAreaContext(
                    id=area.id,
                    name=area.name,
                    slug=area.slug,
                    city=area.city,
                    overall_score=area.overall_score,
                    infrastructure_score=area.infrastructure_score,
                    cleanliness_score=area.cleanliness_score,
                    safety_score=area.safety_score,
                    participation_score=area.participation_score,
                    responsiveness_score=area.responsiveness_score,
                    environment_score=area.environment_score,
                )
                for area in areas
            ],
            active_issues=[
                MissionIssueContext(
                    id=issue.id,
                    public_reference=issue.public_reference,
                    title=issue.title,
                    ai_summary=issue.ai_summary,
                    category=issue.category.value,
                    severity=issue.severity.value,
                    urgency_level=issue.urgency_level.value,
                    suggested_department=issue.suggested_department,
                    location=issue.location,
                    landmark=issue.landmark,
                    status=issue.status.value,
                    area_id=issue.area_id,
                    age_days=max((now - _aware_datetime(issue.created_at)).days, 0),
                )
                for issue in issues
            ],
            existing_active_missions=[
                MissionActiveContext(
                    id=mission.id,
                    title=mission.title,
                    area_id=mission.area_id,
                    mission_type=mission.mission_type.value,
                    category=mission.category.value if mission.category else None,
                    target_count=mission.target_count,
                    progress_count=mission.progress_count,
                    expires_at=mission.expires_at.isoformat()
                    if mission.expires_at
                    else None,
                )
                for mission in missions
            ],
        )

    def list_public(self) -> list[Mission]:
        return list(
            self._session.scalars(
                select(Mission)
                .where(Mission.status == MissionStatus.ACTIVE)
                .options(selectinload(Mission.area), selectinload(Mission.actions))
                .order_by(
                    Mission.expires_at.is_(None),
                    Mission.expires_at.asc(),
                    Mission.created_at.desc(),
                ),
            ).all(),
        )

    def get_detail(self, mission_id: UUID) -> Mission | None:
        return self._session.scalar(
            select(Mission)
            .where(Mission.id == mission_id)
            .options(selectinload(Mission.area), selectinload(Mission.actions)),
        )

    def list_admin(self) -> list[Mission]:
        return list(
            self._session.scalars(
                select(Mission)
                .options(selectinload(Mission.area), selectinload(Mission.actions))
                .order_by(
                    Mission.status.asc(),
                    Mission.expires_at.is_(None),
                    Mission.expires_at.asc(),
                    Mission.created_at.desc(),
                ),
            ).all(),
        )

    def get_public_detail(self, mission_id: UUID) -> Mission | None:
        return self._session.scalar(
            select(Mission)
            .where(
                Mission.id == mission_id,
                Mission.status.in_(PUBLIC_DETAIL_STATUSES),
            )
            .options(selectinload(Mission.area), selectinload(Mission.actions)),
        )

    def get_active_for_action(self, mission_id: UUID) -> Mission | None:
        return self._session.scalar(
            select(Mission)
            .where(Mission.id == mission_id, Mission.status == MissionStatus.ACTIVE)
            .options(selectinload(Mission.area), selectinload(Mission.actions))
            .with_for_update(),
        )

    def action_counts(self, mission_id: UUID) -> dict[MissionActionType, int]:
        rows = self._session.execute(
            select(MissionAction.action_type, func.count(MissionAction.id))
            .where(MissionAction.mission_id == mission_id)
            .group_by(MissionAction.action_type),
        ).all()
        return {action_type: count for action_type, count in rows}

    def viewer_actions(self, mission_id: UUID, actor_hash: str) -> list[MissionActionType]:
        return list(
            self._session.scalars(
                select(MissionAction.action_type)
                .where(
                    MissionAction.mission_id == mission_id,
                    MissionAction.actor_hash == actor_hash,
                )
                .order_by(MissionAction.created_at, MissionAction.id),
            ).all(),
        )

    def add_action_if_absent(
        self,
        mission_id: UUID,
        action_type: MissionActionType,
        actor_hash: str,
        *,
        issue_id: UUID | None,
    ) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(
                    MissionAction(
                        mission_id=mission_id,
                        issue_id=issue_id,
                        action_type=action_type,
                        actor_hash=actor_hash,
                    ),
                )
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def add_community_action_if_absent(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(
                    CommunityAction(
                        issue_id=issue_id,
                        action_type=action_type,
                        actor_hash=actor_hash,
                    ),
                )
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def flush(self) -> None:
        self._session.flush()
