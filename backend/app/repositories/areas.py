from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.domain.areas import BASELINE_AREA_SCORE, DEFAULT_AREA_CITY, area_slug, normalize_area_name
from app.domain.enums import IssueStatus
from app.domain.missions import MissionStatus
from app.models.area import Area
from app.models.area_score_event import AreaScoreEvent
from app.models.issue import Issue
from app.models.mission import Mission


@dataclass(frozen=True, slots=True)
class AreaRecord:
    area: Area
    open_issues: int
    resolved_this_week: int
    total_issues: int
    active_missions: int = 0
    recent_score_events: list[AreaScoreEvent] | None = None
    active_issues: list[Issue] | None = None


class AreaRepository(Protocol):
    def list_public(self, *, resolved_since: datetime) -> list[AreaRecord]: ...

    def get_by_slug(self, slug: str, *, resolved_since: datetime) -> AreaRecord | None: ...

    def get_for_score_recalculation(self, area_id: UUID) -> Area | None: ...

    def list_for_score_recalculation(self) -> list[Area]: ...

    def recent_score_events(self, area_id: UUID, *, limit: int) -> list[AreaScoreEvent]: ...

    def active_issues(self, area_id: UUID, *, limit: int) -> list[Issue]: ...

    def add_score_event(self, event: AreaScoreEvent) -> AreaScoreEvent: ...

    def flush(self) -> None: ...


class SQLAlchemyAreaRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_public(self, *, resolved_since: datetime) -> list[AreaRecord]:
        open_count = self._open_issue_count()
        resolved_count = self._resolved_issue_count(resolved_since)
        total_count = func.count(Issue.id).label("total_issues")
        active_missions = self._active_mission_count()
        rows = self._session.execute(
            select(Area, open_count, resolved_count, total_count, active_missions)
            .outerjoin(Issue, Issue.area_id == Area.id)
            .group_by(Area.id)
            .order_by(Area.rank.is_(None), Area.rank.asc(), Area.name.asc()),
        ).all()
        return [
            AreaRecord(
                area=area,
                open_issues=open_issues,
                resolved_this_week=resolved_this_week,
                total_issues=total_issues,
                active_missions=active_missions,
            )
            for area, open_issues, resolved_this_week, total_issues, active_missions in rows
        ]

    def get_by_slug(self, slug: str, *, resolved_since: datetime) -> AreaRecord | None:
        open_count = self._open_issue_count()
        resolved_count = self._resolved_issue_count(resolved_since)
        total_count = func.count(Issue.id).label("total_issues")
        active_missions = self._active_mission_count()
        row = self._session.execute(
            select(Area, open_count, resolved_count, total_count, active_missions)
            .outerjoin(Issue, Issue.area_id == Area.id)
            .where(Area.slug == slug)
            .group_by(Area.id),
        ).one_or_none()
        if row is None:
            return None
        area, open_issues, resolved_this_week, total_issues, active_missions = row
        return AreaRecord(
            area=area,
            open_issues=open_issues,
            resolved_this_week=resolved_this_week,
            total_issues=total_issues,
            active_missions=active_missions,
            recent_score_events=self.recent_score_events(area.id, limit=8),
            active_issues=self.active_issues(area.id, limit=6),
        )

    def get_for_score_recalculation(self, area_id: UUID) -> Area | None:
        return self._session.scalar(
            select(Area)
            .where(Area.id == area_id)
            .options(
                selectinload(Area.issues).selectinload(Issue.community_actions),
            )
            .with_for_update(),
        )

    def list_for_score_recalculation(self) -> list[Area]:
        return list(
            self._session.scalars(
                select(Area)
                .options(
                    selectinload(Area.issues).selectinload(Issue.community_actions),
                )
                .order_by(Area.name, Area.id)
                .with_for_update(),
            ).all(),
        )

    def recent_score_events(self, area_id: UUID, *, limit: int) -> list[AreaScoreEvent]:
        return list(
            self._session.scalars(
                select(AreaScoreEvent)
                .where(AreaScoreEvent.area_id == area_id)
                .order_by(AreaScoreEvent.created_at.desc(), AreaScoreEvent.id.desc())
                .limit(limit),
            ).all(),
        )

    def active_issues(self, area_id: UUID, *, limit: int) -> list[Issue]:
        return list(
            self._session.scalars(
                select(Issue)
                .where(
                    Issue.area_id == area_id,
                    Issue.status.not_in((IssueStatus.RESOLVED, IssueStatus.REJECTED)),
                )
                .order_by(Issue.updated_at.desc(), Issue.id.desc())
                .limit(limit),
            ).all(),
        )

    def add_score_event(self, event: AreaScoreEvent) -> AreaScoreEvent:
        self._session.add(event)
        self._session.flush()
        return event

    def flush(self) -> None:
        self._session.flush()

    @staticmethod
    def _open_issue_count() -> ColumnElement[int]:
        return cast(
            ColumnElement[int],
            func.count(
                case(
                    (
                        Issue.status.not_in((IssueStatus.RESOLVED, IssueStatus.REJECTED)),
                        1,
                    ),
                ),
            ).label("open_issues"),
        )

    @staticmethod
    def _resolved_issue_count(resolved_since: datetime) -> ColumnElement[int]:
        return cast(
            ColumnElement[int],
            func.count(
                case(
                    (
                        (Issue.status == IssueStatus.RESOLVED)
                        & (Issue.updated_at >= resolved_since),
                        1,
                    ),
                ),
            ).label("resolved_this_week"),
        )

    @staticmethod
    def _active_mission_count() -> ColumnElement[int]:
        return cast(
            ColumnElement[int],
            select(func.count(Mission.id))
            .where(
                Mission.area_id == Area.id,
                Mission.status == MissionStatus.ACTIVE,
            )
            .correlate(Area)
            .scalar_subquery()
            .label("active_missions"),
        )


def get_or_create_area_for_location(
    session: Session,
    location: str,
    *,
    city: str = DEFAULT_AREA_CITY,
) -> Area:
    name = normalize_area_name(location)
    slug = area_slug(name, city)
    area = session.scalar(select(Area).where(Area.city == city, Area.slug == slug))
    if area is not None:
        return area
    area = Area(
        name=name,
        slug=slug,
        city=city,
        overall_score=BASELINE_AREA_SCORE,
        infrastructure_score=BASELINE_AREA_SCORE,
        cleanliness_score=BASELINE_AREA_SCORE,
        safety_score=BASELINE_AREA_SCORE,
        participation_score=BASELINE_AREA_SCORE,
        responsiveness_score=BASELINE_AREA_SCORE,
        environment_score=BASELINE_AREA_SCORE,
        status_label="improving",
    )
    session.add(area)
    session.flush()
    return area
