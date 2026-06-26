from collections.abc import Generator
from dataclasses import asdict
from datetime import UTC, datetime
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
    UpdateActorType,
    UrgencyLevel,
)
from app.models.civic_operations_report import CivicOperationsReport
from app.models.community_action import CommunityAction
from app.models.issue import Issue
from app.models.issue_update import IssueUpdate
from app.repositories.operations import SQLAlchemyOperationsRepository


@pytest.fixture
def operations_session() -> Generator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()
    engine.dispose()


def make_issue(
    number: int,
    *,
    status: IssueStatus = IssueStatus.REPORTED,
    created_at: datetime | None = None,
) -> Issue:
    created = created_at or datetime(2026, 6, 26, 8, tzinfo=UTC)
    return Issue(
        id=UUID(int=number),
        public_reference=f"CP-20260626-{number:08d}",
        title=f"Civic issue {number}",
        original_description="A detailed citizen report that remains private to normal workflows.",
        ai_summary="A structured issue summary suitable for operations analysis.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        urgency_level=UrgencyLevel.URGENT,
        urgency_reason="Residents use this location frequently.",
        suggested_department="Public Works / Road Maintenance",
        safety_risk="Residents may be harmed if this is ignored.",
        citizen_explanation="Review and track this issue publicly.",
        suggested_next_action="Arrange inspection and mitigation.",
        location="Sector 12",
        landmark="City Public School",
        image_key=f"issues/{number}.jpg",
        image_mime="image/jpeg",
        status=status,
        citizen_name="Private Citizen",
        citizen_contact="private@example.com",
        ai_model="test-model",
        prompt_version="test-v1",
        created_at=created,
        updated_at=created,
    )


def add_action(
    session: Session,
    issue: Issue,
    action_type: CommunityActionType,
    actor_suffix: str,
) -> None:
    session.add(
        CommunityAction(
            issue_id=issue.id,
            action_type=action_type,
            actor_hash=f"{issue.id.hex}-{actor_suffix}",
        ),
    )


def test_active_issues_for_analysis_are_privacy_safe_and_filtered(
    operations_session: Session,
) -> None:
    created = datetime(2026, 6, 25, 6, tzinfo=UTC)
    active = make_issue(1, status=IssueStatus.COMMUNITY_VERIFIED, created_at=created)
    resolved = make_issue(2, status=IssueStatus.RESOLVED, created_at=created)
    rejected = make_issue(3, status=IssueStatus.REJECTED, created_at=created)
    escalated = make_issue(4, status=IssueStatus.ESCALATED, created_at=created)
    operations_session.add_all([active, resolved, rejected, escalated])
    operations_session.flush()
    add_action(operations_session, active, CommunityActionType.SAW_THIS_TOO, "one")
    add_action(operations_session, active, CommunityActionType.SAW_THIS_TOO, "two")
    add_action(operations_session, active, CommunityActionType.STILL_UNRESOLVED, "three")
    add_action(operations_session, active, CommunityActionType.FIXED, "four")
    add_action(operations_session, active, CommunityActionType.INCORRECT, "five")
    add_action(operations_session, resolved, CommunityActionType.SAW_THIS_TOO, "ignored")
    operations_session.add_all(
        [
            IssueUpdate(
                issue_id=active.id,
                from_status=IssueStatus.REPORTED,
                to_status=IssueStatus.COMMUNITY_VERIFIED,
                note="Automatically promoted by community confirmations.",
                actor_type=UpdateActorType.SYSTEM,
                created_at=datetime(2026, 6, 25, 7, tzinfo=UTC),
            ),
            IssueUpdate(
                issue_id=active.id,
                from_status=IssueStatus.COMMUNITY_VERIFIED,
                to_status=IssueStatus.ESCALATED,
                note="Escalated to road maintenance for urgent review.",
                actor_type=UpdateActorType.ADMIN,
                created_at=datetime(2026, 6, 25, 8, tzinfo=UTC),
            ),
        ],
    )
    operations_session.commit()

    records = SQLAlchemyOperationsRepository(operations_session).active_issues_for_analysis(
        current_time=datetime(2026, 6, 27, 6, tzinfo=UTC),
    )

    assert [record.issue_id for record in records] == [str(active.id), str(escalated.id)]
    first = records[0]
    assert first.public_reference == "CP-20260626-00000001"
    assert first.department == "Public Works / Road Maintenance"
    assert first.status == "community_verified"
    assert first.verification_count == 2
    assert first.unresolved_count == 1
    assert first.fixed_count == 1
    assert first.incorrect_count == 1
    assert first.age_hours == 48
    assert first.age_days == 2
    assert first.latest_admin_update == "Escalated to road maintenance for urgent review."
    assert "citizen_contact" not in asdict(first)
    assert "private@example.com" not in str(asdict(first))


def test_operations_reports_are_saved_and_latest_report_is_loaded(
    operations_session: Session,
) -> None:
    repository = SQLAlchemyOperationsRepository(operations_session)
    older = repository.add_report(
        CivicOperationsReport(
            generated_at=datetime(2026, 6, 25, 10, tzinfo=UTC),
            total_issues_analyzed=1,
            model_used="gemini-test",
            executive_summary="Older report.",
            urgent_issues_json=[{"issue_id": "older"}],
            duplicate_clusters_json=[],
            area_hotspots_json=[],
            department_priorities_json=[],
            escalation_messages_json=[],
            predicted_risks_json=[],
            raw_response_json={"executive_summary": "Older report."},
        ),
    )
    newer = repository.add_report(
        CivicOperationsReport(
            generated_at=datetime(2026, 6, 26, 10, tzinfo=UTC),
            total_issues_analyzed=2,
            model_used="gemini-test",
            executive_summary="Newer report.",
            urgent_issues_json=[{"issue_id": "newer"}],
            duplicate_clusters_json=[{"cluster_title": "Possible duplicate"}],
            area_hotspots_json=[{"area": "Sector 12"}],
            department_priorities_json=[{"department": "Public Works"}],
            escalation_messages_json=[{"message": "Please inspect."}],
            predicted_risks_json=[{"risk": "Accident risk."}],
            raw_response_json={"executive_summary": "Newer report."},
        ),
    )
    operations_session.commit()

    latest = repository.latest_report()

    assert older.id != newer.id
    assert latest is not None
    assert latest.id == newer.id
    assert latest.total_issues_analyzed == 2
    assert latest.urgent_issues_json == [{"issue_id": "newer"}]
    assert latest.raw_response_json["executive_summary"] == "Newer report."


def test_latest_report_returns_none_when_no_report_exists(operations_session: Session) -> None:
    assert SQLAlchemyOperationsRepository(operations_session).latest_report() is None
