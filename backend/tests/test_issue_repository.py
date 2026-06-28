from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueSort,
    IssueStatus,
    UrgencyLevel,
)
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.repositories.issues import SQLAlchemyIssueRepository
from app.schemas.issues import IssueListQuery


def make_issue(
    number: int,
    *,
    category: IssueCategory = IssueCategory.ROAD_DAMAGE,
    severity: IssueSeverity = IssueSeverity.MEDIUM,
    status: IssueStatus = IssueStatus.REPORTED,
    location: str = "Sector 12",
    created_offset: int = 0,
) -> Issue:
    created_at = datetime(2026, 6, 25, 10, tzinfo=UTC) + timedelta(minutes=created_offset)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-20260625-{number:08d}",
        title=f"Civic issue {number}",
        original_description="A sufficiently detailed original issue description.",
        ai_summary="A sufficiently detailed structured civic issue summary.",
        category=category,
        severity=severity,
        urgency_level=UrgencyLevel.SOON,
        urgency_reason="Residents use this area throughout the day.",
        suggested_department="Public Works",
        safety_risk="The issue may affect residents using this area.",
        citizen_explanation="This report has been structured for public tracking.",
        suggested_next_action="Verify the issue and arrange an inspection.",
        location=location,
        landmark=None,
        image_key=f"issues/{number}.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name=f"Private Citizen {number}",
        citizen_contact=f"private-{number}@example.com",
        ai_model="test-model",
        prompt_version="test-v1",
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.fixture
def tracker_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def add_confirmations(session: Session, issue: Issue, count: int) -> None:
    session.add_all(
        [
            CommunityAction(
                issue_id=issue.id,
                action_type=CommunityActionType.SAW_THIS_TOO,
                actor_hash=f"{issue.id.hex}-{index}",
            )
            for index in range(count)
        ],
    )


def test_combined_filters_and_location_search(tracker_session: Session) -> None:
    matching = make_issue(
        1,
        category=IssueCategory.STREETLIGHT,
        severity=IssueSeverity.HIGH,
        status=IssueStatus.IN_PROGRESS,
        location="Green Park Extension",
    )
    tracker_session.add_all(
        [
            matching,
            make_issue(2, category=IssueCategory.STREETLIGHT, location="Green Park"),
            make_issue(3, severity=IssueSeverity.HIGH, location="Green Park"),
            make_issue(4, status=IssueStatus.IN_PROGRESS, location="Old Town"),
        ],
    )
    tracker_session.commit()

    records, total = SQLAlchemyIssueRepository(tracker_session).list_public(
        IssueListQuery(
            category=IssueCategory.STREETLIGHT,
            severity=IssueSeverity.HIGH,
            status=IssueStatus.IN_PROGRESS,
            location="green park",
        ),
    )

    assert total == 1
    assert [record.issue.id for record in records] == [matching.id]


def test_sorting_and_stable_pagination(tracker_session: Session) -> None:
    issues = [
        make_issue(1, severity=IssueSeverity.LOW, created_offset=0),
        make_issue(2, severity=IssueSeverity.CRITICAL, created_offset=1),
        make_issue(3, severity=IssueSeverity.HIGH, created_offset=2),
        make_issue(4, severity=IssueSeverity.MEDIUM, created_offset=3),
        make_issue(5, severity=IssueSeverity.HIGH, created_offset=4),
    ]
    tracker_session.add_all(issues)
    tracker_session.flush()
    add_confirmations(tracker_session, issues[0], 2)
    add_confirmations(tracker_session, issues[2], 4)
    add_confirmations(tracker_session, issues[4], 4)
    tracker_session.add(
        CommunityAction(
            issue_id=issues[1].id,
            action_type=CommunityActionType.FIXED,
            actor_hash="fixed-does-not-count",
        ),
    )
    tracker_session.commit()
    repository = SQLAlchemyIssueRepository(tracker_session)

    newest_page_one, total = repository.list_public(IssueListQuery(page=1, page_size=2))
    newest_page_two, _ = repository.list_public(IssueListQuery(page=2, page_size=2))
    oldest, _ = repository.list_public(IssueListQuery(sort=IssueSort.OLDEST))
    verified, _ = repository.list_public(IssueListQuery(sort=IssueSort.MOST_VERIFIED))
    severity, _ = repository.list_public(IssueListQuery(sort=IssueSort.SEVERITY))

    assert total == 5
    assert [record.issue.id.int for record in newest_page_one] == [5, 4]
    assert [record.issue.id.int for record in newest_page_two] == [3, 2]
    assert [record.issue.id.int for record in oldest] == [1, 2, 3, 4, 5]
    assert [(record.issue.id.int, record.verification_count) for record in verified[:3]] == [
        (5, 4),
        (3, 4),
        (1, 2),
    ]
    assert [record.issue.id.int for record in severity] == [2, 5, 3, 4, 1]


def test_duplicate_issues_are_redirect_details_not_tracker_items(
    tracker_session: Session,
) -> None:
    current_time = datetime.now(UTC)
    original = make_issue(20)
    recent_duplicate = make_issue(21, status=IssueStatus.DUPLICATE)
    recent_duplicate.duplicate_of = original
    recent_duplicate.duplicate_of_issue_id = original.id
    recent_duplicate.duplicate_marked_at = current_time
    stale_original = make_issue(22)
    stale_duplicate = make_issue(23, status=IssueStatus.DUPLICATE)
    stale_duplicate.duplicate_of = stale_original
    stale_duplicate.duplicate_of_issue_id = stale_original.id
    stale_duplicate.duplicate_marked_at = current_time - timedelta(days=3)
    tracker_session.add_all([original, recent_duplicate, stale_original, stale_duplicate])
    tracker_session.commit()
    repository = SQLAlchemyIssueRepository(tracker_session)

    records, total = repository.list_public(IssueListQuery())
    recent_detail = repository.get_public_detail(recent_duplicate.id)
    stale_detail = repository.get_public_detail(stale_duplicate.id)

    assert total == 2
    assert {record.issue.id for record in records} == {original.id, stale_original.id}
    assert recent_detail is not None
    assert recent_detail.duplicate_of is not None
    assert recent_detail.duplicate_of.id == original.id
    assert stale_detail is None

    original.status = IssueStatus.RESOLVED
    tracker_session.commit()
    tracker_session.expire_all()

    assert repository.get_public_detail(recent_duplicate.id) is None
