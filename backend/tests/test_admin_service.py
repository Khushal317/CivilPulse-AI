from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.repositories.admin_issues import AdminIssueRecord, AdminIssueRepository
from app.schemas.admin import AdminIssueListQuery, AdminStatusUpdateRequest
from app.services.admin import AdminService


def make_issue(status: IssueStatus = IssueStatus.REPORTED) -> Issue:
    created_at = datetime(2026, 6, 25, tzinfo=UTC)
    issue = Issue(
        id=UUID(int=1),
        public_reference="CP-20260625-00000001",
        title="Pothole near school",
        original_description="A resident reported a deep pothole near a school.",
        ai_summary="A road defect creates a risk for riders and pedestrians.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        urgency_level=UrgencyLevel.URGENT,
        urgency_reason="Children and riders use the road.",
        suggested_department="Public Works",
        safety_risk="Riders may lose control.",
        citizen_explanation="The issue requires an administrator review.",
        suggested_next_action="Arrange an inspection.",
        location="Sector 12",
        landmark="City School",
        image_key="issues/one.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name="Private Citizen",
        citizen_contact="private@example.com",
        ai_model="gemini-test",
        prompt_version="v1",
        area_id=UUID(int=30),
        created_at=created_at,
        updated_at=created_at,
    )
    issue.updates = []
    return issue


class FakeAdminIssueRepository(AdminIssueRepository):
    def __init__(self, issue: Issue) -> None:
        self.issue = issue
        self.updates: list[IssueUpdate] = []

    def dashboard_counts(self) -> dict[str, int]:
        return {
            "total_reports": 10,
            "high_severity": 4,
            "verified": 3,
            "pending": 7,
            "resolved": 2,
        }

    def category_counts(self) -> dict[IssueCategory, int]:
        return {IssueCategory.ROAD_DAMAGE: 6, IssueCategory.STREETLIGHT: 4}

    def latest(self, limit: int) -> list[AdminIssueRecord]:
        assert limit == 6
        return [AdminIssueRecord(self.issue, 3)]

    def priority(self, limit: int) -> list[AdminIssueRecord]:
        assert limit == 6
        return [AdminIssueRecord(self.issue, 3)]

    def list_admin(self, query: AdminIssueListQuery) -> tuple[list[AdminIssueRecord], int]:
        del query
        return [AdminIssueRecord(self.issue, 3)], 1

    def get_detail(self, issue_id: UUID) -> Issue | None:
        return self.issue if issue_id == self.issue.id else None

    def get_for_update(self, issue_id: UUID) -> Issue | None:
        return self.get_detail(issue_id)

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]:
        assert issue_id == self.issue.id
        return {CommunityActionType.SAW_THIS_TOO: 3}

    def add_update(self, update: IssueUpdate) -> IssueUpdate:
        update.id = UUID(int=len(self.updates) + 10)
        update.created_at = datetime(2026, 6, 25, 12, tzinfo=UTC)
        self.updates.append(update)
        return update

    def flush(self) -> None:
        return None


class FakeAreaScoreTrigger:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, IssueStatus, str]] = []

    def recalculate_issue_area(self, issue: Issue, *, event_type: str) -> None:
        self.calls.append((issue.id, issue.status, event_type))


def test_dashboard_and_admin_detail_include_authorized_private_fields() -> None:
    repository = FakeAdminIssueRepository(make_issue())
    service = AdminService(repository)

    dashboard = service.dashboard()
    detail = service.get_issue(UUID(int=1))

    assert dashboard.metrics.total_reports == 10
    assert dashboard.category_breakdown[0].count == 6
    assert dashboard.latest_reports[0].verification_count == 3
    assert detail.citizen_name == "Private Citizen"
    assert detail.citizen_contact == "private@example.com"


def test_valid_transition_creates_public_admin_timeline_note() -> None:
    issue = make_issue()
    repository = FakeAdminIssueRepository(issue)
    updated = AdminService(repository).update_status(
        issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.IN_PROGRESS,
            note="Road maintenance team assigned for inspection.",
        ),
    )

    assert updated.status is IssueStatus.IN_PROGRESS
    assert len(repository.updates) == 1
    assert repository.updates[0].from_status is IssueStatus.REPORTED
    assert repository.updates[0].note == "Road maintenance team assigned for inspection."


def test_admin_resolved_rejected_and_restored_statuses_trigger_civic_genome() -> None:
    resolved_issue = make_issue()
    resolved_trigger = FakeAreaScoreTrigger()
    AdminService(
        FakeAdminIssueRepository(resolved_issue),
        area_score_trigger=resolved_trigger,
    ).update_status(
        resolved_issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.RESOLVED,
            note="Road repair completed and verified by field staff.",
        ),
    )

    rejected_issue = make_issue()
    rejected_repository = FakeAdminIssueRepository(rejected_issue)
    rejected_trigger = FakeAreaScoreTrigger()
    service = AdminService(rejected_repository, area_score_trigger=rejected_trigger)
    service.update_status(
        rejected_issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.REJECTED,
            rejection_reason="Duplicate of an existing public issue.",
        ),
    )
    service.update_status(
        rejected_issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.REPORTED,
            note="Restored after administrator review.",
        ),
    )

    assert resolved_trigger.calls == [
        (resolved_issue.id, IssueStatus.RESOLVED, "admin_resolved"),
    ]
    assert rejected_trigger.calls == [
        (rejected_issue.id, IssueStatus.REJECTED, "admin_rejected"),
        (rejected_issue.id, IssueStatus.REPORTED, "admin_restored"),
    ]


def test_invalid_transition_and_missing_rejection_reason_are_rejected() -> None:
    service = AdminService(FakeAdminIssueRepository(make_issue(IssueStatus.RESOLVED)))
    with pytest.raises(AppError) as invalid:
        service.update_status(
            UUID(int=1),
            AdminStatusUpdateRequest(to_status=IssueStatus.REJECTED, rejection_reason="Invalid"),
        )
    assert invalid.value.code == "invalid_status_transition"

    with pytest.raises(ValueError):
        AdminStatusUpdateRequest(to_status=IssueStatus.REJECTED)


def test_rejection_reason_is_public_timeline_note_and_rejected_can_be_restored() -> None:
    issue = make_issue()
    repository = FakeAdminIssueRepository(issue)
    service = AdminService(repository)

    rejected = service.update_status(
        issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.REJECTED,
            rejection_reason="Duplicate of an existing public issue.",
        ),
    )
    restored = service.update_status(
        issue.id,
        AdminStatusUpdateRequest(
            to_status=IssueStatus.REPORTED,
            note="Restored after administrator review.",
        ),
    )

    assert rejected.updates[-1].note == "Duplicate of an existing public issue."
    assert restored.status is IssueStatus.REPORTED
    assert len(repository.updates) == 2
