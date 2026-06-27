from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from app.core.errors import AppError
from app.domain.enums import CommunityActionType, IssueCategory, IssueStatus, UpdateActorType
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.repositories.admin_issues import AdminIssueRecord, AdminIssueRepository
from app.schemas.admin import (
    AdminDashboardMetrics,
    AdminDashboardResponse,
    AdminIssueDetail,
    AdminIssueListQuery,
    AdminIssueListResponse,
    AdminIssueSummary,
    AdminStatusUpdateRequest,
    CategoryMetric,
)
from app.schemas.issues import CommunityCounts, IssueUpdatePublic
from app.services.areas import AreaScoreTrigger

VALID_TRANSITIONS: dict[IssueStatus, frozenset[IssueStatus]] = {
    IssueStatus.REPORTED: frozenset(
        {
            IssueStatus.COMMUNITY_VERIFIED,
            IssueStatus.ESCALATED,
            IssueStatus.IN_PROGRESS,
            IssueStatus.RESOLVED,
            IssueStatus.REJECTED,
        },
    ),
    IssueStatus.COMMUNITY_VERIFIED: frozenset(
        {
            IssueStatus.ESCALATED,
            IssueStatus.IN_PROGRESS,
            IssueStatus.RESOLVED,
            IssueStatus.REJECTED,
        },
    ),
    IssueStatus.ESCALATED: frozenset(
        {IssueStatus.IN_PROGRESS, IssueStatus.RESOLVED, IssueStatus.REJECTED},
    ),
    IssueStatus.IN_PROGRESS: frozenset(
        {IssueStatus.ESCALATED, IssueStatus.RESOLVED, IssueStatus.REJECTED},
    ),
    IssueStatus.RESOLVED: frozenset({IssueStatus.IN_PROGRESS}),
    IssueStatus.REJECTED: frozenset({IssueStatus.REPORTED}),
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def image_url(key: str) -> str:
    return f"/api/v1/media/{key}"


def community_counts(values: dict[CommunityActionType, int]) -> CommunityCounts:
    return CommunityCounts(
        saw_this_too=values.get(CommunityActionType.SAW_THIS_TOO, 0),
        still_unresolved=values.get(CommunityActionType.STILL_UNRESOLVED, 0),
        fixed=values.get(CommunityActionType.FIXED, 0),
        incorrect=values.get(CommunityActionType.INCORRECT, 0),
    )


def summary(record: AdminIssueRecord) -> AdminIssueSummary:
    issue = record.issue
    return AdminIssueSummary(
        id=issue.id,
        public_reference=issue.public_reference,
        title=issue.title,
        category=issue.category,
        severity=issue.severity,
        status=issue.status,
        location=issue.location,
        landmark=issue.landmark,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        verification_count=record.verification_count,
    )


@dataclass(slots=True)
class AdminService:
    repository: AdminIssueRepository
    area_score_trigger: AreaScoreTrigger | None = None

    def dashboard(self) -> AdminDashboardResponse:
        counts = self.repository.dashboard_counts()
        categories = self.repository.category_counts()
        return AdminDashboardResponse(
            metrics=AdminDashboardMetrics(**counts),
            category_breakdown=[
                CategoryMetric(category=category, count=categories.get(category, 0))
                for category in IssueCategory
            ],
            latest_reports=[summary(record) for record in self.repository.latest(6)],
            priority_issues=[summary(record) for record in self.repository.priority(6)],
        )

    def list_issues(self, query: AdminIssueListQuery) -> AdminIssueListResponse:
        records, total = self.repository.list_admin(query)
        return AdminIssueListResponse(
            items=[summary(record) for record in records],
            page=query.page,
            page_size=query.page_size,
            total_items=total,
            total_pages=ceil(total / query.page_size) if total else 0,
        )

    def get_issue(self, issue_id: UUID) -> AdminIssueDetail:
        issue = self.repository.get_detail(issue_id)
        if issue is None:
            raise self._not_found()
        return self._detail(issue)

    def update_status(
        self,
        issue_id: UUID,
        request: AdminStatusUpdateRequest,
    ) -> AdminIssueDetail:
        issue = self.repository.get_for_update(issue_id)
        if issue is None:
            raise self._not_found()
        if request.to_status == issue.status:
            raise AppError(
                code="status_unchanged",
                message="The issue already has that status.",
                status_code=409,
            )
        if request.to_status not in VALID_TRANSITIONS[issue.status]:
            raise AppError(
                code="invalid_status_transition",
                message=f"An issue cannot move from {issue.status} to {request.to_status}.",
                status_code=409,
            )

        previous = issue.status
        note = (
            request.rejection_reason
            if request.to_status is IssueStatus.REJECTED
            else request.note
        )
        issue.status = request.to_status
        issue.updated_at = now_utc()
        update = self.repository.add_update(
            IssueUpdate(
                issue_id=issue.id,
                from_status=previous,
                to_status=request.to_status,
                note=note,
                actor_type=UpdateActorType.ADMIN,
            ),
        )
        issue.updates = [*issue.updates, update]
        self.repository.flush()
        self._recalculate_issue_area(issue, request.to_status)
        return self._detail(issue)

    def _detail(self, issue: Issue) -> AdminIssueDetail:
        counts = community_counts(self.repository.community_counts(issue.id))
        return AdminIssueDetail(
            id=issue.id,
            public_reference=issue.public_reference,
            title=issue.title,
            category=issue.category,
            severity=issue.severity,
            status=issue.status,
            location=issue.location,
            landmark=issue.landmark,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
            verification_count=counts.saw_this_too,
            original_description=issue.original_description,
            ai_summary=issue.ai_summary,
            urgency_level=issue.urgency_level.value,
            urgency_reason=issue.urgency_reason,
            suggested_department=issue.suggested_department,
            safety_risk=issue.safety_risk,
            citizen_explanation=issue.citizen_explanation,
            suggested_next_action=issue.suggested_next_action,
            image_url=image_url(issue.image_key),
            image_mime=issue.image_mime,
            citizen_name=issue.citizen_name,
            citizen_contact=issue.citizen_contact,
            ai_model=issue.ai_model,
            prompt_version=issue.prompt_version,
            community_counts=counts,
            updates=[
                IssueUpdatePublic.model_validate(update)
                for update in sorted(issue.updates, key=lambda item: item.created_at)
            ],
        )

    @staticmethod
    def _not_found() -> AppError:
        return AppError(
            code="issue_not_found",
            message="The issue was not found.",
            status_code=404,
        )

    def _recalculate_issue_area(self, issue: Issue, to_status: IssueStatus) -> None:
        if self.area_score_trigger is None:
            return
        if to_status is IssueStatus.RESOLVED:
            event_type = "admin_resolved"
        elif to_status is IssueStatus.REJECTED:
            event_type = "admin_rejected"
        elif to_status is IssueStatus.REPORTED:
            event_type = "admin_restored"
        else:
            return
        self.area_score_trigger.recalculate_issue_area(issue, event_type=event_type)
