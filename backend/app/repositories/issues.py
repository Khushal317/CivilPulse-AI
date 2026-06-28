from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.domain.enums import CommunityActionType, IssueSort, IssueStatus
from app.domain.issue_duplicates import DUPLICATE_PUBLIC_RETENTION, now_utc
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.schemas.issues import IssueListQuery, IssueMapQuery


@dataclass(frozen=True, slots=True)
class IssueListRecord:
    issue: Issue
    verification_count: int


class IssueRepository(Protocol):
    def get_by_id(self, issue_id: UUID) -> Issue | None: ...

    def add(self, issue: Issue) -> Issue: ...

    def list_public(self, query: IssueListQuery) -> tuple[list[IssueListRecord], int]: ...

    def list_public_map(self, query: IssueMapQuery) -> tuple[list[Issue], int]: ...

    def get_public_detail(self, issue_id: UUID) -> Issue | None: ...

    def get_for_update(self, issue_id: UUID) -> Issue | None: ...

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]: ...

    def viewer_actions(self, issue_id: UUID, actor_hash: str) -> list[CommunityActionType]: ...

    def count_actor_actions_since(self, actor_hash: str, since: datetime) -> int: ...

    def add_action_if_absent(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> bool: ...

    def add_update(self, update: IssueUpdate) -> IssueUpdate: ...

    def flush(self) -> None: ...


def _filtered_issue_ids(query: IssueListQuery | IssueMapQuery) -> Select[tuple[UUID]]:
    statement = select(Issue.id).where(Issue.status != IssueStatus.DUPLICATE)
    if query.category is not None:
        statement = statement.where(Issue.category == query.category)
    if query.severity is not None:
        statement = statement.where(Issue.severity == query.severity)
    if query.status is not None:
        statement = statement.where(Issue.status == query.status)
    if query.location:
        statement = statement.where(
            Issue.location.icontains(query.location.strip(), autoescape=True),
        )
    return statement


def _public_detail_visibility_filter(
    original_issue: Any,
    duplicate_cutoff: datetime,
) -> ColumnElement[bool]:
    return or_(
        Issue.status != IssueStatus.DUPLICATE,
        and_(
            Issue.status == IssueStatus.DUPLICATE,
            Issue.duplicate_marked_at > duplicate_cutoff,
            Issue.duplicate_of_issue_id.is_not(None),
            original_issue.status != IssueStatus.RESOLVED,
        ),
    )


def _issue_order(
    query: IssueListQuery,
    verification_count: ColumnElement[int],
) -> tuple[ColumnElement[Any], ...]:
    if query.sort is IssueSort.OLDEST:
        return (Issue.created_at.asc(), Issue.id.asc())
    if query.sort is IssueSort.MOST_VERIFIED:
        return (verification_count.desc(), Issue.created_at.desc(), Issue.id.desc())
    if query.sort is IssueSort.SEVERITY:
        severity_rank = case(
            (Issue.severity == "critical", 4),
            (Issue.severity == "high", 3),
            (Issue.severity == "medium", 2),
            else_=1,
        )
        return (severity_rank.desc(), Issue.created_at.desc(), Issue.id.desc())
    return (Issue.created_at.desc(), Issue.id.desc())


class SQLAlchemyIssueRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, issue_id: UUID) -> Issue | None:
        return self._session.get(Issue, issue_id)

    def add(self, issue: Issue) -> Issue:
        self._session.add(issue)
        self._session.flush()
        return issue

    def list_public(self, query: IssueListQuery) -> tuple[list[IssueListRecord], int]:
        filtered_ids = _filtered_issue_ids(query).subquery()
        total = self._session.scalar(select(func.count()).select_from(filtered_ids)) or 0
        verification_count = func.count(CommunityAction.id).label("verification_count")
        statement = (
            select(Issue, verification_count)
            .join(filtered_ids, filtered_ids.c.id == Issue.id)
            .outerjoin(
                CommunityAction,
                and_(
                    CommunityAction.issue_id == Issue.id,
                    CommunityAction.action_type == CommunityActionType.SAW_THIS_TOO,
                ),
            )
            .group_by(Issue.id)
            .order_by(*_issue_order(query, verification_count))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        records = [
            IssueListRecord(issue=issue, verification_count=verification_count)
            for issue, verification_count in self._session.execute(statement).all()
        ]
        return records, total

    def list_public_map(self, query: IssueMapQuery) -> tuple[list[Issue], int]:
        filtered_ids = _filtered_issue_ids(query).subquery()
        total = self._session.scalar(select(func.count()).select_from(filtered_ids)) or 0
        statement = (
            select(Issue)
            .join(filtered_ids, filtered_ids.c.id == Issue.id)
            .where(Issue.latitude.is_not(None), Issue.longitude.is_not(None))
            .options(selectinload(Issue.area))
            .order_by(Issue.created_at.desc(), Issue.id.desc())
        )
        return list(self._session.scalars(statement).all()), total

    def get_public_detail(self, issue_id: UUID) -> Issue | None:
        original_issue = aliased(Issue)
        duplicate_cutoff = now_utc() - DUPLICATE_PUBLIC_RETENTION
        return self._session.scalar(
            select(Issue)
            .outerjoin(original_issue, Issue.duplicate_of_issue_id == original_issue.id)
            .where(Issue.id == issue_id)
            .where(_public_detail_visibility_filter(original_issue, duplicate_cutoff))
            .options(selectinload(Issue.updates), selectinload(Issue.duplicate_of)),
        )

    def get_for_update(self, issue_id: UUID) -> Issue | None:
        return self._session.scalar(
            select(Issue).where(Issue.id == issue_id).with_for_update(),
        )

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]:
        rows = self._session.execute(
            select(CommunityAction.action_type, func.count(CommunityAction.id))
            .where(CommunityAction.issue_id == issue_id)
            .group_by(CommunityAction.action_type),
        ).all()
        return {action_type: count for action_type, count in rows}

    def viewer_actions(self, issue_id: UUID, actor_hash: str) -> list[CommunityActionType]:
        return list(
            self._session.scalars(
                select(CommunityAction.action_type)
                .where(
                    CommunityAction.issue_id == issue_id,
                    CommunityAction.actor_hash == actor_hash,
                )
                .order_by(CommunityAction.created_at, CommunityAction.id),
            ).all(),
        )

    def count_actor_actions_since(self, actor_hash: str, since: datetime) -> int:
        return (
            self._session.scalar(
                select(func.count(CommunityAction.id)).where(
                    CommunityAction.actor_hash == actor_hash,
                    CommunityAction.created_at >= since,
                ),
            )
            or 0
        )

    def add_action_if_absent(
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

    def add_update(self, update: IssueUpdate) -> IssueUpdate:
        self._session.add(update)
        self._session.flush()
        return update

    def flush(self) -> None:
        self._session.flush()
