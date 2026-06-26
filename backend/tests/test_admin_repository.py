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
    IssueStatus,
    UrgencyLevel,
)
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.repositories.admin_issues import SQLAlchemyAdminIssueRepository
from app.schemas.admin import AdminIssueListQuery


def issue(
    number: int,
    severity: IssueSeverity,
    status: IssueStatus,
    category: IssueCategory,
) -> Issue:
    created_at = datetime(2026, 6, 20, tzinfo=UTC) + timedelta(days=number)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-ADMIN-{number:04d}",
        title=f"Administrator test issue {number}",
        original_description="A detailed citizen report for administrator testing.",
        ai_summary="A structured complaint for administrator testing.",
        category=category,
        severity=severity,
        urgency_level=UrgencyLevel.SOON,
        urgency_reason="The issue affects public use.",
        suggested_department="Municipal Operations",
        safety_risk="Residents may face disruption.",
        citizen_explanation="Administrator review is required.",
        suggested_next_action="Inspect the issue.",
        location=f"Sector {number}",
        landmark=None,
        image_key=f"issues/admin-{number}.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name=f"Citizen {number}",
        citizen_contact=f"citizen-{number}@example.com",
        ai_model="test",
        prompt_version="test",
        created_at=created_at,
        updated_at=created_at,
    )


@pytest.fixture
def admin_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def test_dashboard_aggregates_priority_and_admin_search(admin_session: Session) -> None:
    issues = [
        issue(1, IssueSeverity.HIGH, IssueStatus.REPORTED, IssueCategory.ROAD_DAMAGE),
        issue(2, IssueSeverity.CRITICAL, IssueStatus.COMMUNITY_VERIFIED, IssueCategory.STREETLIGHT),
        issue(3, IssueSeverity.MEDIUM, IssueStatus.RESOLVED, IssueCategory.ROAD_DAMAGE),
        issue(4, IssueSeverity.LOW, IssueStatus.REJECTED, IssueCategory.OTHER),
    ]
    admin_session.add_all(issues)
    admin_session.flush()
    admin_session.add_all(
        [
            CommunityAction(
                issue_id=issues[0].id,
                action_type=CommunityActionType.SAW_THIS_TOO,
                actor_hash=f"actor-{index}",
            )
            for index in range(3)
        ],
    )
    admin_session.commit()
    repository = SQLAlchemyAdminIssueRepository(admin_session)

    counts = repository.dashboard_counts()
    categories = repository.category_counts()
    priority = repository.priority(10)
    search_results, total = repository.list_admin(
        AdminIssueListQuery(search="sector 2", status=IssueStatus.COMMUNITY_VERIFIED),
    )

    assert counts == {
        "total_reports": 4,
        "high_severity": 2,
        "verified": 1,
        "pending": 2,
        "resolved": 1,
    }
    assert categories[IssueCategory.ROAD_DAMAGE] == 2
    assert [record.issue.id.int for record in priority] == [2, 1]
    assert priority[1].verification_count == 3
    assert total == 1
    assert search_results[0].issue.id.int == 2
