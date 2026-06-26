from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.domain.enums import CommunityActionType, IssueCategory, IssueStatus
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.schemas.admin import AdminIssueListQuery


@dataclass(frozen=True, slots=True)
class AdminIssueRecord:
    issue: Issue
    verification_count: int


class AdminIssueRepository(Protocol):
    def dashboard_counts(self) -> dict[str, int]: ...

    def category_counts(self) -> dict[IssueCategory, int]: ...

    def latest(self, limit: int) -> list[AdminIssueRecord]: ...

    def priority(self, limit: int) -> list[AdminIssueRecord]: ...

    def list_admin(self, query: AdminIssueListQuery) -> tuple[list[AdminIssueRecord], int]: ...

    def get_detail(self, issue_id: UUID) -> Issue | None: ...

    def get_for_update(self, issue_id: UUID) -> Issue | None: ...

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]: ...

    def add_update(self, update: IssueUpdate) -> IssueUpdate: ...

    def flush(self) -> None: ...


def verification_count_expression() -> ColumnElement[int]:
    return func.count(
        case(
            (CommunityAction.action_type == CommunityActionType.SAW_THIS_TOO, 1),
        ),
    ).label("verification_count")


def issue_records(statement: Select[Any], session: Session) -> list[AdminIssueRecord]:
    return [
        AdminIssueRecord(issue=issue, verification_count=verification_count)
        for issue, verification_count in session.execute(statement).all()
    ]


class SQLAlchemyAdminIssueRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def dashboard_counts(self) -> dict[str, int]:
        row = self._session.execute(
            select(
                func.count(Issue.id),
                func.count(
                    case(
                        (
                            Issue.severity.in_(("high", "critical")),
                            1,
                        ),
                    ),
                ),
                func.count(case((Issue.status == IssueStatus.COMMUNITY_VERIFIED, 1))),
                func.count(
                    case(
                        (
                            Issue.status.in_(
                                (
                                    IssueStatus.REPORTED,
                                    IssueStatus.COMMUNITY_VERIFIED,
                                    IssueStatus.ESCALATED,
                                    IssueStatus.IN_PROGRESS,
                                ),
                            ),
                            1,
                        ),
                    ),
                ),
                func.count(case((Issue.status == IssueStatus.RESOLVED, 1))),
            ),
        ).one()
        return {
            "total_reports": row[0],
            "high_severity": row[1],
            "verified": row[2],
            "pending": row[3],
            "resolved": row[4],
        }

    def category_counts(self) -> dict[IssueCategory, int]:
        return {
            category: count
            for category, count in self._session.execute(
                select(Issue.category, func.count(Issue.id))
                .group_by(Issue.category)
                .order_by(Issue.category),
            ).all()
        }

    def latest(self, limit: int) -> list[AdminIssueRecord]:
        verification_count = verification_count_expression()
        statement = (
            select(Issue, verification_count)
            .outerjoin(CommunityAction, CommunityAction.issue_id == Issue.id)
            .group_by(Issue.id)
            .order_by(Issue.created_at.desc(), Issue.id.desc())
            .limit(limit)
        )
        return issue_records(statement, self._session)

    def priority(self, limit: int) -> list[AdminIssueRecord]:
        verification_count = verification_count_expression()
        severity_rank = case(
            (Issue.severity == "critical", 2),
            (Issue.severity == "high", 1),
            else_=0,
        )
        statement = (
            select(Issue, verification_count)
            .outerjoin(CommunityAction, CommunityAction.issue_id == Issue.id)
            .where(
                Issue.severity.in_(("high", "critical")),
                Issue.status.not_in((IssueStatus.RESOLVED, IssueStatus.REJECTED)),
            )
            .group_by(Issue.id)
            .order_by(
                severity_rank.desc(),
                verification_count.desc(),
                Issue.created_at.asc(),
                Issue.id.asc(),
            )
            .limit(limit)
        )
        return issue_records(statement, self._session)

    def list_admin(self, query: AdminIssueListQuery) -> tuple[list[AdminIssueRecord], int]:
        filters = []
        if query.search:
            term = query.search.strip()
            filters.append(
                or_(
                    Issue.title.icontains(term, autoescape=True),
                    Issue.location.icontains(term, autoescape=True),
                    Issue.public_reference.icontains(term, autoescape=True),
                ),
            )
        if query.category is not None:
            filters.append(Issue.category == query.category)
        if query.severity is not None:
            filters.append(Issue.severity == query.severity)
        if query.status is not None:
            filters.append(Issue.status == query.status)

        total = self._session.scalar(select(func.count(Issue.id)).where(*filters)) or 0
        verification_count = verification_count_expression()
        statement = (
            select(Issue, verification_count)
            .outerjoin(CommunityAction, CommunityAction.issue_id == Issue.id)
            .where(*filters)
            .group_by(Issue.id)
            .order_by(Issue.updated_at.desc(), Issue.id.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        return issue_records(statement, self._session), total

    def get_detail(self, issue_id: UUID) -> Issue | None:
        return self._session.scalar(
            select(Issue)
            .where(Issue.id == issue_id)
            .options(selectinload(Issue.updates)),
        )

    def get_for_update(self, issue_id: UUID) -> Issue | None:
        return self._session.scalar(
            select(Issue)
            .where(Issue.id == issue_id)
            .options(selectinload(Issue.updates))
            .with_for_update(),
        )

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]:
        return {
            action_type: count
            for action_type, count in self._session.execute(
                select(CommunityAction.action_type, func.count(CommunityAction.id))
                .where(CommunityAction.issue_id == issue_id)
                .group_by(CommunityAction.action_type),
            ).all()
        }

    def add_update(self, update: IssueUpdate) -> IssueUpdate:
        self._session.add(update)
        self._session.flush()
        return update

    def flush(self) -> None:
        self._session.flush()
