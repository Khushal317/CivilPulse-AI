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
from app.repositories.operations import SQLAlchemyOperationsRepository
from app.services.operations import OperationsService
from app.services.operations_ai import DemoCivicOperationsAnalyzer


@pytest.fixture
def acceptance_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def make_acceptance_issue(
    number: int,
    *,
    category: IssueCategory,
    severity: IssueSeverity,
    status: IssueStatus,
    location: str,
    department: str,
) -> Issue:
    created_at = datetime(2026, 6, 20, 9, tzinfo=UTC) + timedelta(hours=number)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-ACCEPT-{number:04d}",
        title=f"{category.value.replace('_', ' ').title()} acceptance issue {number}",
        original_description=(
            "Private citizen report body with contact private@example.com that must not "
            "reach operations responses."
        ),
        ai_summary=f"Structured {category.value} issue in {location} for operations review.",
        category=category,
        severity=severity,
        urgency_level=UrgencyLevel.IMMEDIATE
        if severity is IssueSeverity.CRITICAL
        else UrgencyLevel.URGENT,
        urgency_reason="The issue affects daily public movement.",
        suggested_department=department,
        safety_risk="Residents may face disruption or injury until reviewed.",
        citizen_explanation="This is an acceptance-test issue.",
        suggested_next_action="Coordinate inspection and mitigation.",
        location=location,
        landmark="Acceptance landmark",
        image_key=f"issues/acceptance-{number}.png",
        image_mime="image/png",
        status=status,
        citizen_name="Private Reporter",
        citizen_contact="private@example.com",
        ai_model="acceptance-model",
        prompt_version="acceptance-v1",
        created_at=created_at,
        updated_at=created_at,
    )


def add_confirmations(session: Session, issue: Issue, count: int) -> None:
    for index in range(count):
        session.add(
            CommunityAction(
                issue_id=issue.id,
                action_type=CommunityActionType.SAW_THIS_TOO,
                actor_hash=f"{issue.id.hex}-{index}",
            ),
        )


def test_operations_acceptance_scenario_analyzes_active_issues_without_private_data(
    acceptance_session: Session,
) -> None:
    active_issues = [
        make_acceptance_issue(
            1,
            category=IssueCategory.ROAD_DAMAGE,
            severity=IssueSeverity.HIGH,
            status=IssueStatus.COMMUNITY_VERIFIED,
            location="Sector 12",
            department="Public Works",
        ),
        make_acceptance_issue(
            2,
            category=IssueCategory.WATER_LEAKAGE,
            severity=IssueSeverity.CRITICAL,
            status=IssueStatus.ESCALATED,
            location="Sector 12",
            department="Water Department",
        ),
        make_acceptance_issue(
            3,
            category=IssueCategory.STREETLIGHT,
            severity=IssueSeverity.MEDIUM,
            status=IssueStatus.IN_PROGRESS,
            location="Green Park",
            department="Municipal Lighting",
        ),
        make_acceptance_issue(
            4,
            category=IssueCategory.GARBAGE_WASTE,
            severity=IssueSeverity.HIGH,
            status=IssueStatus.REPORTED,
            location="Old Market",
            department="Sanitation Department",
        ),
    ]
    excluded_issues = [
        make_acceptance_issue(
            5,
            category=IssueCategory.ROAD_DAMAGE,
            severity=IssueSeverity.CRITICAL,
            status=IssueStatus.RESOLVED,
            location="Closed Area",
            department="Public Works",
        ),
        make_acceptance_issue(
            6,
            category=IssueCategory.PUBLIC_SAFETY,
            severity=IssueSeverity.CRITICAL,
            status=IssueStatus.REJECTED,
            location="Rejected Area",
            department="Municipal Safety",
        ),
    ]
    acceptance_session.add_all([*active_issues, *excluded_issues])
    acceptance_session.flush()
    for issue, confirmations in (
        (active_issues[0], 6),
        (active_issues[1], 5),
        (active_issues[2], 4),
        (active_issues[3], 2),
        (excluded_issues[0], 10),
        (excluded_issues[1], 10),
    ):
        add_confirmations(acceptance_session, issue, confirmations)
    acceptance_session.commit()

    response = OperationsService(
        repository=SQLAlchemyOperationsRepository(acceptance_session),
        analyzer=DemoCivicOperationsAnalyzer(),
    ).analyze_active_issues()

    dumped = response.model_dump(mode="json")
    dumped_text = str(dumped)
    referenced_ids = {
        item["issue_id"]
        for section in (
            dumped["urgent_issues"],
            dumped["escalation_messages"],
            dumped["predicted_risks"],
        )
        for item in section
    }

    assert response.total_issues_analyzed == 4
    assert response.urgent_issues
    assert response.area_hotspots
    assert response.department_priorities
    assert response.escalation_messages
    assert response.predicted_risks
    assert str(excluded_issues[0].id) not in referenced_ids
    assert str(excluded_issues[1].id) not in referenced_ids
    assert "private@example.com" not in dumped_text
    assert "Private Reporter" not in dumped_text
