from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import Base
from app.domain.areas import AreaScoreKey, AreaStatusLabel, area_slug
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)
from app.models.area import Area
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.repositories.areas import SQLAlchemyAreaRepository
from app.services.area_scores import (
    clamp_score,
    compute_area_score_snapshot,
    issue_category_score_impact,
    overall_score,
    status_label,
)
from app.services.areas import AreaService


@pytest.fixture
def score_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def make_area(number: int, name: str, *, overall: int = 70) -> Area:
    return Area(
        id=UUID(int=number),
        name=name,
        slug=area_slug(name),
        city="CivicPulse City",
        overall_score=overall,
        infrastructure_score=70,
        cleanliness_score=70,
        safety_score=70,
        participation_score=70,
        responsiveness_score=70,
        environment_score=70,
        status_label="improving",
    )


def make_issue(
    number: int,
    area: Area,
    *,
    category: IssueCategory = IssueCategory.ROAD_DAMAGE,
    severity: IssueSeverity = IssueSeverity.HIGH,
    status: IssueStatus = IssueStatus.REPORTED,
    created_at: datetime | None = None,
) -> Issue:
    timestamp = created_at or datetime(2026, 6, 27, 10, tzinfo=UTC)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-20260627-{number:08d}",
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
        location=area.name,
        landmark=None,
        image_key=f"issues/{number}.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name=None,
        citizen_contact=None,
        ai_model="test-model",
        prompt_version="test-v1",
        area=area,
        created_at=timestamp,
        updated_at=timestamp,
    )


def test_score_helpers_are_deterministic() -> None:
    assert clamp_score(-10) == 0
    assert clamp_score(101) == 100
    assert overall_score(
        {
            AreaScoreKey.INFRASTRUCTURE: 62,
            AreaScoreKey.CLEANLINESS: 81,
            AreaScoreKey.SAFETY: 69,
            AreaScoreKey.PARTICIPATION: 88,
            AreaScoreKey.RESPONSIVENESS: 55,
            AreaScoreKey.ENVIRONMENT: 72,
        },
    ) == 70
    assert status_label(90) is AreaStatusLabel.THRIVING
    assert status_label(70) is AreaStatusLabel.IMPROVING
    assert status_label(55) is AreaStatusLabel.STABLE
    assert status_label(40) is AreaStatusLabel.NEEDS_ATTENTION
    assert status_label(39) is AreaStatusLabel.AT_RISK


def test_issue_category_score_mapping() -> None:
    assert issue_category_score_impact(
        IssueCategory.ROAD_DAMAGE,
        IssueSeverity.HIGH,
    ) == {
        AreaScoreKey.INFRASTRUCTURE: 4,
        AreaScoreKey.SAFETY: 2,
    }
    assert issue_category_score_impact(
        IssueCategory.GARBAGE_WASTE,
        IssueSeverity.MEDIUM,
    ) == {
        AreaScoreKey.CLEANLINESS: 2,
        AreaScoreKey.ENVIRONMENT: 1,
    }
    assert issue_category_score_impact(IssueCategory.OTHER, IssueSeverity.CRITICAL) == {}


def test_compute_area_score_snapshot_uses_issues_and_participation() -> None:
    area = make_area(1, "Sector 12")
    old_high_issue = make_issue(
        1,
        area,
        created_at=datetime(2026, 6, 20, 10, tzinfo=UTC),
    )
    old_high_issue.community_actions = [
        CommunityAction(
            issue_id=old_high_issue.id,
            action_type=CommunityActionType.SAW_THIS_TOO,
            actor_hash=f"actor-{index}",
        )
        for index in range(3)
    ]
    resolved_issue = make_issue(
        2,
        area,
        category=IssueCategory.GARBAGE_WASTE,
        severity=IssueSeverity.MEDIUM,
        status=IssueStatus.RESOLVED,
    )

    snapshot = compute_area_score_snapshot(
        [old_high_issue, resolved_issue],
        current_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
    )

    assert snapshot.scores[AreaScoreKey.INFRASTRUCTURE] == 66
    assert snapshot.scores[AreaScoreKey.CLEANLINESS] == 72
    assert snapshot.scores[AreaScoreKey.SAFETY] == 68
    assert snapshot.scores[AreaScoreKey.PARTICIPATION] == 73
    assert snapshot.scores[AreaScoreKey.RESPONSIVENESS] == 67
    assert snapshot.scores[AreaScoreKey.OVERALL] == 69


def test_area_service_recalculates_scores_events_and_ranks(score_session: Session) -> None:
    sector = make_area(1, "Sector 12")
    green = make_area(2, "Green Park")
    sector.issues = [
        make_issue(
            1,
            sector,
            severity=IssueSeverity.CRITICAL,
            created_at=datetime(2026, 6, 20, 10, tzinfo=UTC),
        ),
    ]
    green.issues = [
            make_issue(
                2,
                green,
                status=IssueStatus.RESOLVED,
            ),
    ]
    score_session.add_all([sector, green])
    score_session.commit()

    count = AreaService(SQLAlchemyAreaRepository(score_session)).recalculate_all_scores()
    score_session.commit()

    assert count == 2
    assert green.rank == 1
    assert sector.rank == 2
    assert sector.status_label == "stable"
    events = SQLAlchemyAreaRepository(score_session).recent_score_events(sector.id, limit=10)
    changed_keys = {event.score_key for event in events}
    assert AreaScoreKey.INFRASTRUCTURE in changed_keys
    assert AreaScoreKey.RESPONSIVENESS in changed_keys
    assert all(event.event_type == "score_recalculated" for event in events)


def test_recalculate_single_area_ranks_against_all_areas(score_session: Session) -> None:
    sector = make_area(1, "Sector 12", overall=70)
    green = make_area(2, "Green Park", overall=70)
    sector.issues = [
        make_issue(
            1,
            sector,
            severity=IssueSeverity.CRITICAL,
            created_at=datetime(2026, 6, 20, 10, tzinfo=UTC),
        ),
    ]
    score_session.add_all([sector, green])
    score_session.commit()

    result = AreaService(SQLAlchemyAreaRepository(score_session)).recalculate_area_scores(
        sector.id,
    )
    score_session.commit()

    assert result.open_issues == 1
    assert result.resolved_this_week == 0
    assert green.rank == 1
    assert sector.rank == 2


def test_recalculate_area_scores_missing_area_raises(score_session: Session) -> None:
    service = AreaService(SQLAlchemyAreaRepository(score_session))

    with pytest.raises(AppError) as caught:
        service.recalculate_area_scores(UUID(int=404))

    assert caught.value.code == "area_not_found"
