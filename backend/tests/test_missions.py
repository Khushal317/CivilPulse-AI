from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.base import Base
from app.domain.areas import area_slug
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)
from app.domain.missions import MissionActionType, MissionStatus, MissionType
from app.models.area import Area
from app.models.issue import Issue
from app.models.mission import Mission
from app.models.mission_action import MissionAction
from app.repositories.missions import SQLAlchemyMissionRepository
from app.schemas.missions import MissionAreaSummary, MissionSummary
from app.services.missions import MissionService


@pytest.fixture
def mission_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def make_area() -> Area:
    return Area(
        id=UUID(int=1),
        name="Sector 12",
        slug=area_slug("Sector 12"),
        city="CivicPulse City",
        overall_score=70,
        infrastructure_score=70,
        cleanliness_score=70,
        safety_score=70,
        participation_score=70,
        responsiveness_score=70,
        environment_score=70,
        rank=1,
        status_label="improving",
    )


def make_mission(
    number: int,
    area: Area,
    *,
    status: MissionStatus = MissionStatus.ACTIVE,
    progress_count: int = 1,
) -> Mission:
    now = datetime(2026, 6, 27, 10, tzinfo=UTC)
    return Mission(
        id=UUID(int=number),
        title=f"Verify safe road repairs {number}",
        area=area,
        mission_type=MissionType.VERIFICATION,
        status=status,
        goal_description="Confirm whether the reported road repair is visible and safe.",
        target_count=5,
        progress_count=progress_count,
        category=IssueCategory.ROAD_DAMAGE,
        reward_json={"points": 20, "score_key": "participation"},
        ai_reason="This area has recent road-damage reports that need community verification.",
        linked_issue_ids_json=[str(UUID(int=99))],
        model_used="test-generator",
        raw_response_json={"source": "test"},
        expires_at=now + timedelta(days=7),
        published_at=None if status is MissionStatus.DRAFT else now,
        completed_at=now if status is MissionStatus.COMPLETED else None,
        created_at=now,
        updated_at=now,
    )


def make_issue(number: int, area: Area) -> Issue:
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-20260627-{number:08d}",
        title=f"Streetlight issue {number}",
        original_description="A public streetlight is not working.",
        ai_summary="A public streetlight outage needs review.",
        category=IssueCategory.STREETLIGHT,
        severity=IssueSeverity.MEDIUM,
        urgency_level=UrgencyLevel.SOON,
        urgency_reason="Visibility is reduced in the evening.",
        suggested_department="Electricity / Streetlighting",
        safety_risk="Pedestrians may have reduced visibility.",
        citizen_explanation="The public light should be checked.",
        suggested_next_action="Verify the outage and assign repair.",
        location="Sector 12",
        landmark="Central Park",
        image_key=f"issues/{number}.jpg",
        image_mime="image/jpeg",
        status=IssueStatus.COMMUNITY_VERIFIED,
        citizen_name=None,
        citizen_contact=None,
        ai_model="test",
        prompt_version="test",
        area=area,
    )


def test_mission_schema_validates_lifecycle_fields() -> None:
    area = MissionAreaSummary(
        id=UUID(int=1),
        name="Sector 12",
        slug="civicpulse-city-sector-12",
        city="CivicPulse City",
    )

    with pytest.raises(ValidationError):
        MissionSummary(
            id=UUID(int=2),
            title="Invalid public mission",
            mission_type=MissionType.VERIFICATION,
            status=MissionStatus.ACTIVE,
            area=area,
            goal_description="Confirm the local issue status.",
            target_count=3,
            progress_count=4,
            category=None,
            reward={},
            ai_reason="Progress cannot exceed target.",
            expires_at=None,
            published_at=datetime(2026, 6, 27, tzinfo=UTC),
            completed_at=None,
            created_at=datetime(2026, 6, 27, tzinfo=UTC),
            updated_at=datetime(2026, 6, 27, tzinfo=UTC),
        )


def test_public_mission_repository_lists_active_and_hides_drafts(
    mission_session: Session,
) -> None:
    area = make_area()
    active = make_mission(10, area)
    completed = make_mission(11, area, status=MissionStatus.COMPLETED, progress_count=5)
    expired = make_mission(13, area, status=MissionStatus.EXPIRED, progress_count=3)
    draft = make_mission(12, area, status=MissionStatus.DRAFT, progress_count=0)
    mission_session.add(area)
    repository = SQLAlchemyMissionRepository(mission_session)
    for mission in (active, completed, expired, draft):
        repository.add(mission)
    mission_session.commit()

    public_list = MissionService(repository).list_public()
    public_detail = MissionService(repository).get_public_detail(completed.id)
    expired_detail = MissionService(repository).get_public_detail(expired.id)

    assert [mission.id for mission in public_list.items] == [active.id]
    assert public_detail.id == completed.id
    assert expired_detail.status is MissionStatus.EXPIRED
    assert public_detail.linked_issue_ids == [UUID(int=99)]
    assert repository.get_public_detail(draft.id) is None


def test_admin_mission_list_groups_all_statuses(mission_session: Session) -> None:
    area = make_area()
    draft = make_mission(10, area, status=MissionStatus.DRAFT, progress_count=0)
    active = make_mission(11, area, status=MissionStatus.ACTIVE, progress_count=1)
    completed = make_mission(12, area, status=MissionStatus.COMPLETED, progress_count=5)
    expired = make_mission(13, area, status=MissionStatus.EXPIRED, progress_count=3)
    mission_session.add(area)
    repository = SQLAlchemyMissionRepository(mission_session)
    for mission in (draft, active, completed, expired):
        repository.add(mission)
    mission_session.commit()

    grouped = MissionService(repository).list_admin()

    assert [mission.id for mission in grouped.drafts] == [draft.id]
    assert [mission.id for mission in grouped.active] == [active.id]
    assert [mission.id for mission in grouped.completed] == [completed.id]
    assert [mission.id for mission in grouped.expired] == [expired.id]


def test_admin_can_publish_expire_and_complete_missions(mission_session: Session) -> None:
    area = make_area()
    draft = make_mission(10, area, status=MissionStatus.DRAFT, progress_count=0)
    active_to_expire = make_mission(11, area, status=MissionStatus.ACTIVE, progress_count=1)
    active_to_complete = make_mission(12, area, status=MissionStatus.ACTIVE, progress_count=2)
    mission_session.add(area)
    repository = SQLAlchemyMissionRepository(mission_session)
    for mission in (draft, active_to_expire, active_to_complete):
        repository.add(mission)
    mission_session.commit()

    service = MissionService(repository)
    published = service.publish(draft.id)
    expired = service.expire(active_to_expire.id)
    completed = service.complete(active_to_complete.id)

    assert published.status is MissionStatus.ACTIVE
    assert published.published_at is not None
    assert expired.status is MissionStatus.EXPIRED
    assert expired.completed_at is None
    assert completed.status is MissionStatus.COMPLETED
    assert completed.progress_count == completed.target_count
    assert completed.completed_at is not None


def test_admin_mission_lifecycle_rejects_invalid_transitions(
    mission_session: Session,
) -> None:
    area = make_area()
    draft = make_mission(10, area, status=MissionStatus.DRAFT, progress_count=0)
    completed = make_mission(11, area, status=MissionStatus.COMPLETED, progress_count=5)
    mission_session.add(area)
    repository = SQLAlchemyMissionRepository(mission_session)
    for mission in (draft, completed):
        repository.add(mission)
    mission_session.commit()
    service = MissionService(repository)

    with pytest.raises(AppError) as publish_error:
        service.publish(completed.id)
    with pytest.raises(AppError) as expire_error:
        service.expire(draft.id)
    with pytest.raises(AppError) as complete_error:
        service.complete(draft.id)

    assert publish_error.value.code == "mission_not_publishable"
    assert expire_error.value.code == "mission_not_expirable"
    assert complete_error.value.code == "mission_not_completable"


def test_mission_actions_prevent_duplicate_global_actor_actions(
    mission_session: Session,
) -> None:
    area = make_area()
    mission = make_mission(10, area)
    mission_session.add_all([area, mission])
    mission_session.commit()

    mission_session.add(
        MissionAction(
            mission_id=mission.id,
            issue_id=None,
            action_type=MissionActionType.JOINED,
            actor_hash="actor-one",
        ),
    )
    mission_session.commit()
    mission_session.add(
        MissionAction(
            mission_id=mission.id,
            issue_id=None,
            action_type=MissionActionType.JOINED,
            actor_hash="actor-one",
        ),
    )

    with pytest.raises(IntegrityError):
        mission_session.commit()


def test_mission_join_and_volunteer_increment_progress_once(
    mission_session: Session,
) -> None:
    area = make_area()
    mission = make_mission(10, area, progress_count=0)
    mission_session.add_all([area, mission])
    mission_session.commit()

    service = MissionService(SQLAlchemyMissionRepository(mission_session))
    joined = service.submit_action(mission.id, MissionActionType.JOINED, "actor-one")
    repeated = service.submit_action(mission.id, MissionActionType.JOINED, "actor-one")
    volunteered = service.submit_action(mission.id, MissionActionType.VOLUNTEERED, "actor-one")

    assert joined.accepted is True
    assert joined.progress_count == 1
    assert joined.joined_count == 1
    assert repeated.accepted is False
    assert repeated.progress_count == 1
    assert volunteered.accepted is True
    assert volunteered.progress_count == 2
    assert set(volunteered.viewer_actions) == {
        MissionActionType.JOINED,
        MissionActionType.VOLUNTEERED,
    }


def test_mission_linked_issue_actions_create_community_signals(
    mission_session: Session,
) -> None:
    area = make_area()
    issue = make_issue(99, area)
    mission = make_mission(10, area, progress_count=0)
    mission_session.add_all([area, issue, mission])
    mission_session.commit()

    service = MissionService(SQLAlchemyMissionRepository(mission_session))
    verified = service.submit_action(
        mission.id,
        MissionActionType.VERIFIED_ISSUE,
        "actor-one",
        issue_id=issue.id,
    )
    unresolved = service.submit_action(
        mission.id,
        MissionActionType.CONFIRMED_UNRESOLVED,
        "actor-one",
        issue_id=issue.id,
    )
    fixed = service.submit_action(
        mission.id,
        MissionActionType.CONFIRMED_FIXED,
        "actor-one",
        issue_id=issue.id,
    )

    counts = SQLAlchemyMissionRepository(mission_session).action_counts(mission.id)
    community_rows = {
        action.action_type
        for action in issue.community_actions
        if action.actor_hash == "actor-one"
    }
    assert verified.progress_count == 1
    assert unresolved.progress_count == 2
    assert fixed.progress_count == 3
    assert counts[MissionActionType.VERIFIED_ISSUE] == 1
    assert community_rows == {
        CommunityActionType.SAW_THIS_TOO,
        CommunityActionType.STILL_UNRESOLVED,
        CommunityActionType.FIXED,
    }


def test_mission_linked_issue_actions_require_linked_issue(
    mission_session: Session,
) -> None:
    area = make_area()
    mission = make_mission(10, area)
    mission_session.add_all([area, mission])
    mission_session.commit()
    service = MissionService(SQLAlchemyMissionRepository(mission_session))

    with pytest.raises(AppError) as missing:
        service.submit_action(mission.id, MissionActionType.VERIFIED_ISSUE, "actor-one")
    with pytest.raises(AppError) as unlinked:
        service.submit_action(
            mission.id,
            MissionActionType.VERIFIED_ISSUE,
            "actor-one",
            issue_id=UUID(int=123),
        )
    with pytest.raises(AppError) as not_allowed:
        service.submit_action(
            mission.id,
            MissionActionType.JOINED,
            "actor-one",
            issue_id=UUID(int=99),
        )

    assert missing.value.code == "mission_issue_required"
    assert unlinked.value.code == "mission_issue_not_linked"
    assert not_allowed.value.code == "mission_issue_not_allowed"


def test_completed_and_expired_missions_reject_public_actions(
    mission_session: Session,
) -> None:
    area = make_area()
    completed = make_mission(10, area, status=MissionStatus.COMPLETED, progress_count=5)
    expired = make_mission(11, area, status=MissionStatus.EXPIRED, progress_count=2)
    mission_session.add_all([area, completed, expired])
    mission_session.commit()
    service = MissionService(SQLAlchemyMissionRepository(mission_session))

    with pytest.raises(AppError) as completed_error:
        service.submit_action(completed.id, MissionActionType.JOINED, "actor-one")
    with pytest.raises(AppError) as expired_error:
        service.submit_action(expired.id, MissionActionType.JOINED, "actor-one")

    assert completed_error.value.code == "mission_completed"
    assert expired_error.value.code == "mission_expired"
