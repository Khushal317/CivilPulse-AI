from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.areas import area_slug
from app.domain.enums import IssueCategory
from app.domain.missions import MissionActionType, MissionStatus, MissionType
from app.models.area import Area
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
