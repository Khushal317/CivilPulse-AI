from io import BytesIO
from pathlib import Path

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)
from app.repositories.admin_issues import SQLAlchemyAdminIssueRepository
from app.repositories.issues import SQLAlchemyIssueRepository
from app.repositories.reports import SQLAlchemyReportRepository
from app.schemas.admin import AdminStatusUpdateRequest
from app.schemas.issues import AIAnalysis, AIReportInput, ReportAnalysisInput
from app.services.admin import AdminService
from app.services.ai import CivicIssueAnalyzer
from app.services.images import validate_image
from app.services.issues import IssueService
from app.services.reports import ReportService
from app.services.storage import LocalImageStorage


class AcceptanceAnalyzer(CivicIssueAnalyzer):
    model_name = "acceptance-fake-gemini"

    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis:
        assert b"PNG" in image_bytes[:16]
        assert image_mime == "image/png"
        assert report.location == "Sector 12"
        return AIAnalysis(
            title="Severe pothole near school gate",
            ai_summary="A deep pothole creates a road safety risk near the school entrance.",
            category=IssueCategory.ROAD_DAMAGE,
            severity=IssueSeverity.HIGH,
            urgency_level=UrgencyLevel.URGENT,
            urgency_reason="Children and two-wheel riders use this road every day.",
            suggested_department="Public Works / Road Maintenance",
            safety_risk="Riders may lose control near the school entrance.",
            citizen_explanation="Review the structured complaint before publishing.",
            suggested_next_action="Publish the issue so the community can verify it.",
        )


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color=(90, 90, 90)).save(output, format="PNG")
    return output.getvalue()


def test_complete_pothole_near_school_acceptance_flow(tmp_path: Path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = Settings(
        anonymous_actor_secret="acceptance-actor-secret",
        report_draft_ttl_minutes=60,
    )
    storage = LocalImageStorage(tmp_path)

    try:
        with Session(engine) as session:
            report_service = ReportService(
                repository=SQLAlchemyReportRepository(session),
                storage=storage,
                analyzer=AcceptanceAnalyzer(),
                settings=settings,
            )
            issue_service = IssueService(
                repository=SQLAlchemyIssueRepository(session),
                settings=settings,
            )
            admin_service = AdminService(
                repository=SQLAlchemyAdminIssueRepository(session),
            )

            draft = report_service.analyze(
                ReportAnalysisInput(
                    original_description=(
                        "There is a deep pothole near the school gate and bikes are slipping."
                    ),
                    location="Sector 12",
                    landmark="City Public School",
                    citizen_name="Private Reporter",
                    citizen_contact="private@example.com",
                    urgency_note="Children cross here every morning.",
                ),
                validate_image(png_bytes(), settings),
            )
            published = report_service.publish(draft.id)
            public_before = issue_service.get_public_detail(published.issue_id, "viewer-one")

            assert public_before.status is IssueStatus.REPORTED
            assert public_before.title == "Severe pothole near school gate"
            assert public_before.image_url.startswith("/api/v1/media/issues/")
            assert "private@example.com" not in str(public_before.model_dump())

            for index in range(3):
                result = issue_service.submit_community_action(
                    published.issue_id,
                    CommunityActionType.SAW_THIS_TOO,
                    f"actor-{index}",
                )

            assert result.issue_status is IssueStatus.COMMUNITY_VERIFIED
            assert result.community_counts.saw_this_too == 3

            session.expire_all()
            admin_detail = admin_service.get_issue(published.issue_id)
            assert admin_detail.citizen_contact == "private@example.com"
            assert admin_detail.verification_count == 3

            for status, note in (
                (IssueStatus.ESCALATED, "Escalated to Public Works for inspection."),
                (IssueStatus.IN_PROGRESS, "Road repair team assigned."),
                (IssueStatus.RESOLVED, "Pothole filled and road surface reopened."),
            ):
                admin_service.update_status(
                    published.issue_id,
                    AdminStatusUpdateRequest(to_status=status, note=note),
                )

            session.expire_all()
            public_after = issue_service.get_public_detail(published.issue_id, "viewer-two")

            assert public_after.status is IssueStatus.RESOLVED
            assert [update.to_status for update in public_after.updates] == [
                IssueStatus.REPORTED,
                IssueStatus.COMMUNITY_VERIFIED,
                IssueStatus.ESCALATED,
                IssueStatus.IN_PROGRESS,
                IssueStatus.RESOLVED,
            ]
            assert public_after.updates[-1].note == "Pothole filled and road surface reopened."
    finally:
        engine.dispose()
