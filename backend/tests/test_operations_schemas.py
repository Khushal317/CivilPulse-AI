from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.operations import (
    AreaHotspot,
    OperationsAnalysis,
    OperationsIssueInput,
    OperationsReportResponse,
    UrgentIssueRecommendation,
)


def issue_input_payload() -> dict[str, object]:
    return {
        "issue_id": str(UUID(int=1)),
        "public_reference": "CP-20260626-00000001",
        "title": "Deep pothole beside school crossing",
        "category": "road_damage",
        "department": "Public Works / Road Maintenance",
        "severity": "high",
        "status": "community_verified",
        "location": "Sector 12",
        "landmark": "City Public School",
        "verification_count": 5,
        "unresolved_count": 2,
        "fixed_count": 0,
        "incorrect_count": 0,
        "created_at": "2026-06-24T10:00:00Z",
        "age_hours": 48,
        "age_days": 2,
        "summary": "Large pothole near school gate causing risk to children and riders.",
        "latest_admin_update": "Escalated for inspection.",
    }


def urgent_issue() -> UrgentIssueRecommendation:
    return UrgentIssueRecommendation(
        issue_id=UUID(int=1),
        public_reference="CP-20260626-00000001",
        title="Deep pothole beside school crossing",
        location="Sector 12, near City Public School",
        department="Public Works / Road Maintenance",
        severity=IssueSeverity.HIGH,
        priority_reason="High severity and multiple community confirmations near a school.",
        recommended_action="Inspect and temporarily barricade the affected crossing.",
        suggested_time_window="Within 24 hours",
    )


def test_operations_issue_input_is_strict_and_privacy_safe() -> None:
    payload = issue_input_payload()

    issue = OperationsIssueInput.model_validate(payload)

    assert issue.issue_id == UUID(int=1)
    assert issue.category is IssueCategory.ROAD_DAMAGE
    assert issue.status is IssueStatus.COMMUNITY_VERIFIED
    assert "citizen_contact" not in issue.model_dump()

    with pytest.raises(ValidationError):
        OperationsIssueInput.model_validate({**payload, "citizen_contact": "private@example.com"})


def test_operations_analysis_requires_empty_sections_for_empty_report() -> None:
    empty = OperationsAnalysis(
        total_issues_analyzed=0,
        model_used="system-empty",
        executive_summary="There are no active civic issues to analyze right now.",
    )

    assert empty.urgent_issues == []

    with pytest.raises(ValidationError, match="empty operations reports"):
        OperationsAnalysis(
            total_issues_analyzed=0,
            model_used="bad-empty",
            executive_summary="This empty report incorrectly contains issue recommendations.",
            urgent_issues=[urgent_issue()],
        )


def test_operations_analysis_requires_at_least_one_section_for_active_report() -> None:
    with pytest.raises(ValidationError, match="require at least one section"):
        OperationsAnalysis(
            total_issues_analyzed=1,
            model_used="gemini-test",
            executive_summary="One active issue was analyzed but no sections were returned.",
        )


def test_operations_report_response_serializes_persisted_report_shape() -> None:
    report = OperationsReportResponse(
        id=UUID(int=10),
        generated_at=datetime(2026, 6, 26, 10, tzinfo=UTC),
        created_at=datetime(2026, 6, 26, 10, tzinfo=UTC),
        total_issues_analyzed=1,
        model_used="gemini-test",
        executive_summary="One high-risk road issue needs administrator review.",
        urgent_issues=[urgent_issue()],
        area_hotspots=[
            AreaHotspot(
                area="Sector 12",
                issue_count=1,
                main_categories=[IssueCategory.ROAD_DAMAGE],
                risk_level="high",
                insight="School-zone road damage should be reviewed quickly.",
            ),
        ],
        raw_response={"executive_summary": "One high-risk road issue needs review."},
    )

    dumped = report.model_dump(mode="json")

    assert dumped["id"] == str(UUID(int=10))
    assert dumped["urgent_issues"][0]["severity"] == "high"
    assert dumped["area_hotspots"][0]["main_categories"] == ["road_damage"]
    assert "private@example.com" not in str(dumped)
