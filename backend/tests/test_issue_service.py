from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UpdateActorType,
    UrgencyLevel,
)
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.repositories.issues import IssueListRecord, IssueRepository
from app.schemas.issues import IssueListQuery
from app.services.issues import IssueService


class FakeIssueRepository(IssueRepository):
    def __init__(self, issue: Issue) -> None:
        self.issue = issue
        self.actions: dict[tuple[UUID, str, CommunityActionType], None] = {}
        self.updates: list[IssueUpdate] = []
        self.recent_actor_actions = 0

    def get_by_id(self, issue_id: UUID) -> Issue | None:
        return self.issue if issue_id == self.issue.id else None

    def add(self, issue: Issue) -> Issue:
        return issue

    def list_public(self, query: IssueListQuery) -> tuple[list[IssueListRecord], int]:
        del query
        return [IssueListRecord(issue=self.issue, verification_count=7)], 25

    def get_public_detail(self, issue_id: UUID) -> Issue | None:
        return self.issue if issue_id == self.issue.id else None

    def get_for_update(self, issue_id: UUID) -> Issue | None:
        return self.get_public_detail(issue_id)

    def community_counts(self, issue_id: UUID) -> dict[CommunityActionType, int]:
        return {
            action_type: sum(
                1
                for stored_issue_id, _actor_hash, stored_type in self.actions
                if stored_issue_id == issue_id and stored_type is action_type
            )
            for action_type in CommunityActionType
        }

    def viewer_actions(self, issue_id: UUID, actor_hash: str) -> list[CommunityActionType]:
        return [
            action_type
            for stored_issue_id, stored_actor_hash, action_type in self.actions
            if stored_issue_id == issue_id and stored_actor_hash == actor_hash
        ]

    def count_actor_actions_since(self, actor_hash: str, since: datetime) -> int:
        del actor_hash, since
        return self.recent_actor_actions

    def add_action_if_absent(
        self,
        issue_id: UUID,
        action_type: CommunityActionType,
        actor_hash: str,
    ) -> bool:
        key = (issue_id, actor_hash, action_type)
        if key in self.actions:
            return False
        self.actions[key] = None
        return True

    def add_update(self, update: IssueUpdate) -> IssueUpdate:
        update.id = UUID(int=len(self.updates) + 100)
        update.created_at = datetime(2026, 6, 25, 12, tzinfo=UTC)
        self.updates.append(update)
        self.issue.updates = [*self.issue.updates, update]
        return update

    def flush(self) -> None:
        return None


class FakeAreaScoreTrigger:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, IssueStatus, str]] = []

    def recalculate_issue_area(self, issue: Issue, *, event_type: str) -> None:
        self.calls.append((issue.id, issue.status, event_type))


def test_issue_service_builds_public_page_without_private_fields() -> None:
    created_at = datetime(2026, 6, 25, tzinfo=UTC)
    issue = Issue(
        id=UUID(int=1),
        public_reference="CP-20260625-00000001",
        title="Pothole near school",
        original_description="Private original report description.",
        ai_summary="A structured summary suitable for the public issue detail.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        urgency_level=UrgencyLevel.URGENT,
        urgency_reason="Children use this road.",
        suggested_department="Public Works",
        safety_risk="Riders may lose control.",
        citizen_explanation="Review the report.",
        suggested_next_action="Inspect the road.",
        location="Sector 12",
        landmark="City School",
        image_key="issues/one.jpg",
        image_mime="image/jpeg",
        status=IssueStatus.REPORTED,
        citizen_name="Private Name",
        citizen_contact="private@example.com",
        ai_model="test",
        prompt_version="test",
        area_id=UUID(int=30),
        created_at=created_at,
        updated_at=created_at,
    )

    page = IssueService(FakeIssueRepository(issue), Settings()).list_public(
        IssueListQuery(page=2, page_size=12),
    )

    assert page.page == 2
    assert page.total_items == 25
    assert page.total_pages == 3
    assert page.items[0].image_url == "/api/v1/media/issues/one.jpg"
    assert page.items[0].verification_count == 7
    assert "citizen_contact" not in page.items[0].model_dump()


def make_issue(*, status: IssueStatus = IssueStatus.REPORTED) -> Issue:
    created_at = datetime(2026, 6, 25, tzinfo=UTC)
    issue = Issue(
        id=UUID(int=10),
        public_reference="CP-20260625-00000010",
        title="Unsafe road surface",
        original_description="A resident observed a dangerous road surface near a school.",
        ai_summary="A damaged road surface creates a safety risk for local traffic.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        urgency_level=UrgencyLevel.URGENT,
        urgency_reason="Children and riders use this road every day.",
        suggested_department="Public Works",
        safety_risk="Two-wheel riders may lose control.",
        citizen_explanation="Community members can confirm whether this issue is present.",
        suggested_next_action="Arrange an on-site road inspection.",
        location="Sector 12",
        landmark="City School",
        image_key="issues/ten.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name="Private Name",
        citizen_contact="private@example.com",
        ai_model="test",
        prompt_version="test",
        created_at=created_at,
        updated_at=created_at,
    )
    issue.updates = [
        IssueUpdate(
            id=UUID(int=20),
            issue_id=issue.id,
            from_status=None,
            to_status=IssueStatus.REPORTED,
            note="Issue reported by a citizen.",
            actor_type=UpdateActorType.SYSTEM,
            created_at=created_at,
        ),
    ]
    return issue


def test_three_distinct_confirmations_promote_once() -> None:
    issue = make_issue()
    repository = FakeIssueRepository(issue)
    service = IssueService(repository, Settings())

    first = service.submit_community_action(
        issue.id,
        CommunityActionType.SAW_THIS_TOO,
        "actor-one",
    )
    repeated = service.submit_community_action(
        issue.id,
        CommunityActionType.SAW_THIS_TOO,
        "actor-one",
    )
    service.submit_community_action(issue.id, CommunityActionType.SAW_THIS_TOO, "actor-two")
    third = service.submit_community_action(
        issue.id,
        CommunityActionType.SAW_THIS_TOO,
        "actor-three",
    )
    fourth = service.submit_community_action(
        issue.id,
        CommunityActionType.SAW_THIS_TOO,
        "actor-four",
    )

    assert first.accepted is True
    assert repeated.accepted is False
    assert third.issue_status is IssueStatus.COMMUNITY_VERIFIED
    assert fourth.issue_status is IssueStatus.COMMUNITY_VERIFIED
    assert third.community_counts.saw_this_too == 3
    assert len(repository.updates) == 1
    assert repository.updates[0].to_status is IssueStatus.COMMUNITY_VERIFIED


def test_fixed_signal_is_advisory_and_does_not_resolve() -> None:
    issue = make_issue()
    service = IssueService(FakeIssueRepository(issue), Settings())

    result = service.submit_community_action(
        issue.id,
        CommunityActionType.FIXED,
        "actor-fixed",
    )

    assert result.accepted is True
    assert result.community_counts.fixed == 1
    assert result.issue_status is IssueStatus.REPORTED


def test_accepted_community_actions_trigger_civic_genome_without_duplicate_farming() -> None:
    issue = make_issue()
    trigger = FakeAreaScoreTrigger()
    service = IssueService(FakeIssueRepository(issue), Settings(), area_score_trigger=trigger)

    service.submit_community_action(issue.id, CommunityActionType.SAW_THIS_TOO, "actor-one")
    service.submit_community_action(issue.id, CommunityActionType.SAW_THIS_TOO, "actor-one")
    service.submit_community_action(issue.id, CommunityActionType.STILL_UNRESOLVED, "actor-one")
    service.submit_community_action(issue.id, CommunityActionType.FIXED, "actor-one")
    service.submit_community_action(issue.id, CommunityActionType.INCORRECT, "actor-one")

    assert trigger.calls == [
        (issue.id, IssueStatus.REPORTED, "community_action_saw_this_too"),
        (issue.id, IssueStatus.REPORTED, "community_action_still_unresolved"),
        (issue.id, IssueStatus.REPORTED, "community_action_fixed"),
    ]


def test_invalid_status_does_not_promote_and_rejected_disables_actions() -> None:
    resolved = make_issue(status=IssueStatus.RESOLVED)
    resolved_repository = FakeIssueRepository(resolved)
    resolved_service = IssueService(resolved_repository, Settings())
    for actor in ("one", "two", "three"):
        resolved_service.submit_community_action(
            resolved.id,
            CommunityActionType.SAW_THIS_TOO,
            actor,
        )

    assert resolved.status is IssueStatus.RESOLVED
    assert resolved_repository.updates == []

    rejected = make_issue(status=IssueStatus.REJECTED)
    with pytest.raises(AppError) as caught:
        IssueService(FakeIssueRepository(rejected), Settings()).submit_community_action(
            rejected.id,
            CommunityActionType.INCORRECT,
            "actor",
        )
    assert caught.value.code == "community_actions_unavailable"

    duplicate = make_issue(status=IssueStatus.DUPLICATE)
    with pytest.raises(AppError) as duplicate_caught:
        IssueService(FakeIssueRepository(duplicate), Settings()).submit_community_action(
            duplicate.id,
            CommunityActionType.SAW_THIS_TOO,
            "actor",
        )
    assert duplicate_caught.value.code == "community_actions_unavailable"


def test_duplicate_public_detail_links_to_original_issue() -> None:
    original = make_issue()
    original.id = UUID(int=11)
    duplicate = make_issue(status=IssueStatus.DUPLICATE)
    duplicate.duplicate_of = original
    duplicate.duplicate_of_issue_id = original.id
    duplicate.duplicate_marked_at = datetime(2026, 6, 26, 10, tzinfo=UTC)

    detail = IssueService(FakeIssueRepository(duplicate), Settings()).get_public_detail(
        duplicate.id,
        "viewer",
    )

    assert detail.status is IssueStatus.DUPLICATE
    assert detail.duplicate_of is not None
    assert detail.duplicate_of.id == original.id
    assert detail.duplicate_marked_at == duplicate.duplicate_marked_at


def test_rate_limit_and_public_detail_privacy() -> None:
    issue = make_issue()
    repository = FakeIssueRepository(issue)
    repository.recent_actor_actions = 2
    service = IssueService(
        repository,
        Settings(community_action_rate_limit=2),
    )

    detail = service.get_public_detail(issue.id, "viewer")
    assert detail.updates[0].note == "Issue reported by a citizen."
    assert "citizen_name" not in detail.model_dump()
    assert "citizen_contact" not in detail.model_dump()

    with pytest.raises(AppError) as caught:
        service.submit_community_action(
            issue.id,
            CommunityActionType.STILL_UNRESOLVED,
            "viewer",
        )
    assert caught.value.code == "community_action_rate_limited"
