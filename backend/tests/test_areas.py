from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.areas import area_slug, normalize_area_name
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus, UrgencyLevel
from app.models.area import Area
from app.models.issue import Issue
from app.repositories.areas import (
    SQLAlchemyAreaRepository,
    get_or_create_area_for_location,
)


@pytest.fixture
def area_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def make_area(name: str = "Sector 12") -> Area:
    return Area(
        id=UUID(int=100),
        name=name,
        slug=area_slug(name),
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
        score_events=[],
    )


def make_issue(
    number: int,
    area: Area,
    *,
    status: IssueStatus = IssueStatus.REPORTED,
    updated_at: datetime | None = None,
) -> Issue:
    timestamp = updated_at or datetime(2026, 6, 27, 10, tzinfo=UTC)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-20260627-{number:08d}",
        title=f"Civic issue {number}",
        original_description="A sufficiently detailed original issue description.",
        ai_summary="A sufficiently detailed structured civic issue summary.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.MEDIUM,
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


def test_area_name_and_slug_are_stable() -> None:
    assert normalize_area_name("  Sector   12  ") == "Sector 12"
    assert area_slug("Sector 12") == "civicpulse-city-sector-12"
    assert area_slug("Málaga Road!") == "civicpulse-city-malaga-road"


def test_get_or_create_area_for_location_is_idempotent(area_session: Session) -> None:
    first = get_or_create_area_for_location(area_session, "  Sector   12  ")
    second = get_or_create_area_for_location(area_session, "Sector 12")

    assert first.id == second.id
    assert first.name == "Sector 12"
    assert first.overall_score == 70
    assert first.status_label == "improving"


def test_area_repository_returns_aggregates(area_session: Session) -> None:
    area = make_area()
    now = datetime(2026, 6, 27, 10, tzinfo=UTC)
    area_session.add(area)
    area_session.add_all(
        [
            make_issue(1, area, status=IssueStatus.REPORTED, updated_at=now),
            make_issue(2, area, status=IssueStatus.IN_PROGRESS, updated_at=now),
            make_issue(3, area, status=IssueStatus.RESOLVED, updated_at=now),
            make_issue(
                4,
                area,
                status=IssueStatus.RESOLVED,
                updated_at=now - timedelta(days=10),
            ),
            make_issue(5, area, status=IssueStatus.REJECTED, updated_at=now),
        ],
    )
    area_session.commit()

    records = SQLAlchemyAreaRepository(area_session).list_public(
        resolved_since=now - timedelta(days=7),
    )

    assert len(records) == 1
    assert records[0].area.name == "Sector 12"
    assert records[0].open_issues == 2
    assert records[0].resolved_this_week == 1
    assert records[0].total_issues == 5
