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
from app.domain.missions import MissionActionType, MissionStatus, MissionType
from app.repositories.admin_issues import SQLAlchemyAdminIssueRepository
from app.repositories.areas import SQLAlchemyAreaRepository
from app.repositories.issues import SQLAlchemyIssueRepository
from app.repositories.missions import MissionContext, SQLAlchemyMissionRepository
from app.repositories.reports import SQLAlchemyReportRepository
from app.schemas.admin import AdminStatusUpdateRequest
from app.schemas.issues import AIAnalysis, AIReportInput, ReportAnalysisInput
from app.schemas.missions import GeneratedMissionCandidate, MissionGenerationPayload
from app.services.admin import AdminService
from app.services.ai import CivicIssueAnalyzer
from app.services.areas import AreaService
from app.services.images import validate_image
from app.services.issues import IssueService
from app.services.mission_generation import MissionGenerationService
from app.services.missions import MissionService
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


class AcceptanceMissionGenerator:
    model_name = "acceptance-fake-gemini-mission"

    def generate(self, context: MissionContext) -> MissionGenerationPayload:
        assert context.areas
        assert context.active_issues
        issue = context.active_issues[0]
        assert issue.area_id is not None
        return MissionGenerationPayload(
            missions=[
                GeneratedMissionCandidate(
                    title="Verify school gate road safety",
                    area_id=issue.area_id,
                    mission_type=MissionType.VERIFICATION,
                    goal_description=(
                        "Ask nearby residents to safely confirm whether the school gate "
                        "road issue is still visible from public space."
                    ),
                    target_count=1,
                    category=IssueCategory.ROAD_DAMAGE,
                    reward={"points": 20, "score_key": "participation"},
                    ai_reason=(
                        "A community-verified road damage report near a school needs one "
                        "fresh public confirmation before administrators close the loop."
                    ),
                    linked_issue_ids=[issue.id],
                    expires_in_days=7,
                ),
            ],
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
            area_repository = SQLAlchemyAreaRepository(session)
            area_service = AreaService(repository=area_repository)
            mission_repository = SQLAlchemyMissionRepository(session)
            mission_service = MissionService(
                repository=mission_repository,
                reward_trigger=area_service,
            )
            report_service = ReportService(
                repository=SQLAlchemyReportRepository(session),
                storage=storage,
                analyzer=AcceptanceAnalyzer(),
                settings=settings,
                area_score_trigger=area_service,
            )
            issue_service = IssueService(
                repository=SQLAlchemyIssueRepository(session),
                settings=settings,
                area_score_trigger=area_service,
            )
            admin_service = AdminService(
                repository=SQLAlchemyAdminIssueRepository(session),
                area_score_trigger=area_service,
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

            mission_generation = MissionGenerationService(
                mission_repository,
                AcceptanceMissionGenerator(),
            ).generate_drafts()
            draft_mission = mission_generation.created_drafts[0]

            assert mission_generation.model_used == "acceptance-fake-gemini-mission"
            assert draft_mission.status is MissionStatus.DRAFT
            assert draft_mission.linked_issue_ids == [published.issue_id]

            active_mission = mission_service.publish(draft_mission.id)
            mission_action = mission_service.submit_action(
                active_mission.id,
                MissionActionType.JOINED,
                "mission-actor",
            )

            assert mission_action.accepted is True
            assert mission_action.mission_status is MissionStatus.COMPLETED
            assert mission_action.progress_count == 1

            session.expire_all()
            area_record = area_repository.get_by_slug(
                "civicpulse-city-sector-12",
                resolved_since=public_before.created_at,
            )
            assert area_record is not None
            mission_reward_events = [
                event
                for event in area_repository.recent_score_events(area_record.area.id, limit=20)
                if event.event_type == "mission_completed"
            ]
            assert any(
                event.related_mission_id == active_mission.id
                for event in mission_reward_events
            )
            assert area_record.area.participation_score >= 70

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
