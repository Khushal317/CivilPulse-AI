from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import Base
from app.domain.areas import BASELINE_AREA_SCORE, AreaScoreKey, AreaStatusLabel, area_slug
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)
from app.domain.missions import MissionStatus, MissionType
from app.models.area import Area
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.mission import Mission
from app.repositories.areas import SQLAlchemyAreaRepository
from app.services.area_scores import (
    clamp_score,
    compute_area_score_snapshot,
    confidence_level,
    issue_category_score_impact,
    mission_reward_score_impact,
    overall_score,
    score_limit_evaluation,
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


def make_area(number: int, name: str, *, overall: int = BASELINE_AREA_SCORE) -> Area:
    return Area(
        id=UUID(int=number),
        name=name,
        slug=area_slug(name),
        city="CivicPulse City",
        overall_score=overall,
        infrastructure_score=BASELINE_AREA_SCORE,
        cleanliness_score=BASELINE_AREA_SCORE,
        safety_score=BASELINE_AREA_SCORE,
        participation_score=BASELINE_AREA_SCORE,
        responsiveness_score=BASELINE_AREA_SCORE,
        environment_score=BASELINE_AREA_SCORE,
        status_label="stable",
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


def make_mission(
    number: int,
    area: Area,
    *,
    points: int = 20,
    score_key: str = "participation",
    status: MissionStatus = MissionStatus.COMPLETED,
) -> Mission:
    timestamp = datetime(2026, 6, 27, 10, tzinfo=UTC)
    return Mission(
        id=UUID(int=number),
        title=f"Community mission {number}",
        area=area,
        mission_type=MissionType.VERIFICATION,
        status=status,
        goal_description="Safely verify a public civic issue.",
        target_count=5,
        progress_count=5 if status is MissionStatus.COMPLETED else 2,
        category=IssueCategory.STREETLIGHT,
        reward_json={"points": points, "score_key": score_key},
        ai_reason="Mission helps improve public civic evidence.",
        linked_issue_ids_json=[],
        model_used="test",
        raw_response_json={},
        expires_at=timestamp,
        published_at=timestamp,
        completed_at=timestamp if status is MissionStatus.COMPLETED else None,
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
    ) == 67
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

    assert snapshot.scores[AreaScoreKey.INFRASTRUCTURE] == 46
    assert snapshot.scores[AreaScoreKey.CLEANLINESS] == 52
    assert snapshot.scores[AreaScoreKey.SAFETY] == 48
    assert snapshot.scores[AreaScoreKey.PARTICIPATION] == 53
    assert snapshot.scores[AreaScoreKey.RESPONSIVENESS] == 47
    assert snapshot.scores[AreaScoreKey.OVERALL] == 48


def test_completed_mission_rewards_are_part_of_score_snapshot() -> None:
    area = make_area(1, "Sector 12")
    mission = make_mission(10, area, points=20, score_key="participation")

    snapshot = compute_area_score_snapshot(
        [],
        completed_missions=[mission],
        current_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
    )

    assert mission_reward_score_impact(mission) == {AreaScoreKey.PARTICIPATION: 20}
    assert snapshot.scores[AreaScoreKey.PARTICIPATION] == 70
    assert snapshot.scores[AreaScoreKey.OVERALL] == 50


def test_mission_rewards_ignore_invalid_keys_and_cap_points() -> None:
    area = make_area(1, "Sector 12")
    huge = make_mission(10, area, points=999, score_key="safety")
    overall = make_mission(11, area, points=20, score_key="overall")
    unknown = make_mission(12, area, points=20, score_key="magic")

    snapshot = compute_area_score_snapshot(
        [],
        completed_missions=[huge, overall, unknown],
        current_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
    )

    assert mission_reward_score_impact(huge) == {AreaScoreKey.SAFETY: 20}
    assert mission_reward_score_impact(overall) == {}
    assert mission_reward_score_impact(unknown) == {}
    assert snapshot.scores[AreaScoreKey.SAFETY] == 70
    assert snapshot.scores[AreaScoreKey.OVERALL] == 55


def test_score_limits_cap_dangerous_unresolved_issues() -> None:
    area = make_area(1, "Sector 12")
    critical_old = make_issue(
        1,
        area,
        severity=IssueSeverity.CRITICAL,
        created_at=datetime(2026, 6, 23, 10, tzinfo=UTC),
    )
    high_issues = [
        make_issue(
            number,
            area,
            severity=IssueSeverity.HIGH,
            created_at=datetime(2026, 6, 27, 10, tzinfo=UTC),
        )
        for number in (2, 3, 4)
    ]
    very_old_medium = make_issue(
        5,
        area,
        severity=IssueSeverity.MEDIUM,
        created_at=datetime(2026, 6, 10, 10, tzinfo=UTC),
    )

    limits = score_limit_evaluation(
        [critical_old, *high_issues, very_old_medium],
        current_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
    )
    snapshot = compute_area_score_snapshot(
        [critical_old, *high_issues, very_old_medium],
        current_time=datetime(2026, 6, 27, 10, tzinfo=UTC),
    )

    assert limits.civic_health_cap == 75
    assert limits.responsiveness_cap == 60
    assert "1 critical issue older than 3 days" in limits.reasons
    assert "3 unresolved high-severity issues" in limits.reasons
    assert "1 unresolved issue older than 14 days" in limits.reasons
    assert snapshot.scores[AreaScoreKey.OVERALL] <= 75
    assert snapshot.scores[AreaScoreKey.RESPONSIVENESS] <= 60


def test_confidence_levels_follow_activity_volume() -> None:
    assert confidence_level(2) == "low"
    assert confidence_level(3) == "medium"
    assert confidence_level(10) == "high"


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
    assert sector.status_label == "needs_attention"
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


def test_completed_mission_reward_records_events_and_updates_rank(
    score_session: Session,
) -> None:
    sector = make_area(1, "Sector 12", overall=60)
    green = make_area(2, "Green Park", overall=72)
    sector.missions = [make_mission(10, sector, points=20, score_key="participation")]
    score_session.add_all([sector, green])
    score_session.commit()

    result = AreaService(SQLAlchemyAreaRepository(score_session)).apply_completed_mission_reward(
        sector.missions[0],
    )
    score_session.commit()

    events = SQLAlchemyAreaRepository(score_session).recent_score_events(sector.id, limit=10)
    mission_events = [event for event in events if event.event_type == "mission_completed"]
    assert result.scores.participation == 70
    assert sector.rank == 2
    assert green.rank == 1
    assert mission_events
    assert {event.related_mission_id for event in mission_events} == {sector.missions[0].id}
    assert all("mission completed" in event.reason.lower() for event in mission_events)

    AreaService(SQLAlchemyAreaRepository(score_session)).apply_completed_mission_reward(
        sector.missions[0],
    )
    score_session.commit()
    repeated_events = [
        event
        for event in SQLAlchemyAreaRepository(score_session).recent_score_events(
            sector.id,
            limit=20,
        )
        if event.event_type == "mission_completed"
    ]
    assert len(repeated_events) == len(mission_events)


def test_recalculate_issue_area_records_trigger_metadata(score_session: Session) -> None:
    area = make_area(1, "Sector 12")
    issue = make_issue(1, area, severity=IssueSeverity.CRITICAL)
    area.issues = [issue]
    score_session.add(area)
    score_session.commit()

    AreaService(SQLAlchemyAreaRepository(score_session)).recalculate_issue_area(
        issue,
        event_type="issue_published",
    )
    score_session.commit()

    events = SQLAlchemyAreaRepository(score_session).recent_score_events(area.id, limit=10)
    assert events
    assert {event.event_type for event in events} == {"issue_published"}
    assert {event.related_issue_id for event in events} == {issue.id}
    assert all("published" in event.reason for event in events)


def test_rejected_issue_reverses_active_penalty_without_positive_score_farming(
    score_session: Session,
) -> None:
    area = make_area(1, "Sector 12")
    issue = make_issue(1, area, severity=IssueSeverity.CRITICAL)
    area.issues = [issue]
    score_session.add(area)
    score_session.commit()
    service = AreaService(SQLAlchemyAreaRepository(score_session))

    service.recalculate_issue_area(issue, event_type="issue_published")
    assert area.infrastructure_score < BASELINE_AREA_SCORE
    assert area.overall_score < BASELINE_AREA_SCORE

    issue.status = IssueStatus.REJECTED
    service.recalculate_issue_area(issue, event_type="admin_rejected")
    score_session.commit()

    assert area.infrastructure_score == BASELINE_AREA_SCORE
    assert area.safety_score == BASELINE_AREA_SCORE
    assert area.overall_score == BASELINE_AREA_SCORE
    events = SQLAlchemyAreaRepository(score_session).recent_score_events(area.id, limit=10)
    rejection_events = [event for event in events if event.event_type == "admin_rejected"]
    assert rejection_events
    assert all(event.new_score <= BASELINE_AREA_SCORE for event in rejection_events)


def test_recalculate_area_scores_missing_area_raises(score_session: Session) -> None:
    service = AreaService(SQLAlchemyAreaRepository(score_session))

    with pytest.raises(AppError) as caught:
        service.recalculate_area_scores(UUID(int=404))

    assert caught.value.code == "area_not_found"
