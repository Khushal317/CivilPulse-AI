from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.issues import AIAnalysis, IssueAdminDetail, IssueListItem, IssuePublicDetail


def test_ai_analysis_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        AIAnalysis.model_validate(
            {
                "title": "Unsafe road surface",
                "ai_summary": "A damaged road surface creates a safety risk for local traffic.",
                "category": "not-a-category",
                "severity": IssueSeverity.HIGH,
                "urgency_level": "urgent",
                "urgency_reason": "The issue is close to a school entrance.",
                "suggested_department": "Public Works",
                "safety_risk": "Two-wheelers may lose control.",
                "citizen_explanation": "This should be inspected quickly.",
                "suggested_next_action": "Arrange a road inspection.",
            },
        )


def test_public_issue_schema_cannot_expose_private_fields() -> None:
    public_fields = set(IssuePublicDetail.model_fields)

    assert "citizen_name" not in public_fields
    assert "citizen_contact" not in public_fields
    assert "image_key" not in public_fields
    assert {"citizen_name", "citizen_contact", "image_key"} <= set(
        IssueAdminDetail.model_fields,
    )


def test_issue_list_item_validates_domain_values() -> None:
    item = IssueListItem(
        id=uuid4(),
        public_reference="CP-2026-000001",
        title="Pothole near school gate",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        location="Sector 12",
        landmark="City Public School",
        status=IssueStatus.REPORTED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        verification_count=0,
    )

    assert item.category is IssueCategory.ROAD_DAMAGE
    assert item.status is IssueStatus.REPORTED
