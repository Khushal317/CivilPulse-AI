from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.orm import Session

from app.domain.enums import CommunityActionType, IssueStatus, UpdateActorType
from app.models.civic_operations_report import CivicOperationsReport
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate

ACTIVE_OPERATION_STATUSES = (
    IssueStatus.REPORTED,
    IssueStatus.COMMUNITY_VERIFIED,
    IssueStatus.ESCALATED,
    IssueStatus.IN_PROGRESS,
)


def now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class OperationsIssueRecord:
    issue_id: str
    public_reference: str
    title: str
    category: str
    department: str
    severity: str
    status: str
    location: str
    landmark: str | None
    verification_count: int
    unresolved_count: int
    fixed_count: int
    incorrect_count: int
    created_at: datetime
    age_hours: int
    age_days: int
    summary: str
    latest_admin_update: str | None


class OperationsRepository(Protocol):
    def active_issues_for_analysis(
        self,
        current_time: datetime | None = None,
    ) -> list[OperationsIssueRecord]: ...

    def add_report(self, report: CivicOperationsReport) -> CivicOperationsReport: ...

    def latest_report(self) -> CivicOperationsReport | None: ...


def _count_for(action_type: CommunityActionType) -> Any:
    return func.count(case((CommunityAction.action_type == action_type, 1)))


def _admin_update_subquery() -> Select[tuple[Any, ...]]:
    latest_admin_update = (
        select(
            IssueUpdate.issue_id,
            func.max(IssueUpdate.created_at).label("latest_created_at"),
        )
        .where(IssueUpdate.actor_type == UpdateActorType.ADMIN)
        .group_by(IssueUpdate.issue_id)
        .subquery()
    )
    return (
        select(
            IssueUpdate.issue_id,
            IssueUpdate.note,
        )
        .join(
            latest_admin_update,
            and_(
                latest_admin_update.c.issue_id == IssueUpdate.issue_id,
                latest_admin_update.c.latest_created_at == IssueUpdate.created_at,
            ),
        )
        .where(IssueUpdate.actor_type == UpdateActorType.ADMIN)
    )


class SQLAlchemyOperationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def active_issues_for_analysis(
        self,
        current_time: datetime | None = None,
    ) -> list[OperationsIssueRecord]:
        current = current_time or now_utc()
        admin_updates = _admin_update_subquery().subquery()
        statement = (
            select(
                Issue.id,
                Issue.public_reference,
                Issue.title,
                Issue.category,
                Issue.suggested_department,
                Issue.severity,
                Issue.status,
                Issue.location,
                Issue.landmark,
                _count_for(CommunityActionType.SAW_THIS_TOO).label("verification_count"),
                _count_for(CommunityActionType.STILL_UNRESOLVED).label("unresolved_count"),
                _count_for(CommunityActionType.FIXED).label("fixed_count"),
                _count_for(CommunityActionType.INCORRECT).label("incorrect_count"),
                Issue.created_at,
                Issue.ai_summary,
                admin_updates.c.note.label("latest_admin_update"),
            )
            .outerjoin(CommunityAction, CommunityAction.issue_id == Issue.id)
            .outerjoin(admin_updates, admin_updates.c.issue_id == Issue.id)
            .where(Issue.status.in_(ACTIVE_OPERATION_STATUSES))
            .group_by(Issue.id, admin_updates.c.note)
            .order_by(Issue.created_at.asc(), Issue.id.asc())
        )
        records: list[OperationsIssueRecord] = []
        for row in self._session.execute(statement).all():
            created_at = row.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            age_seconds = max(int((current - created_at).total_seconds()), 0)
            age_hours = age_seconds // 3_600
            records.append(
                OperationsIssueRecord(
                    issue_id=str(row.id),
                    public_reference=row.public_reference,
                    title=row.title,
                    category=row.category.value,
                    department=row.suggested_department,
                    severity=row.severity.value,
                    status=row.status.value,
                    location=row.location,
                    landmark=row.landmark,
                    verification_count=row.verification_count,
                    unresolved_count=row.unresolved_count,
                    fixed_count=row.fixed_count,
                    incorrect_count=row.incorrect_count,
                    created_at=created_at,
                    age_hours=age_hours,
                    age_days=age_hours // 24,
                    summary=row.ai_summary,
                    latest_admin_update=row.latest_admin_update,
                ),
            )
        return records

    def add_report(self, report: CivicOperationsReport) -> CivicOperationsReport:
        self._session.add(report)
        self._session.flush()
        return report

    def latest_report(self) -> CivicOperationsReport | None:
        return self._session.scalar(
            select(CivicOperationsReport).order_by(
                CivicOperationsReport.generated_at.desc(),
                CivicOperationsReport.created_at.desc(),
                CivicOperationsReport.id.desc(),
            ),
        )
