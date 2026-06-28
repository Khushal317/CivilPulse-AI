import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus, UrgencyLevel
from app.models.area import Area
from app.models.issue import Issue
from app.models.issue_draft import IssueDraft
from app.repositories.reports import ReportRepository
from app.schemas.issues import AIAnalysis, AIReportInput, ReportAnalysisInput, ReportDraftUpdate
from app.services.ai import CivicIssueAnalyzer
from app.services.cleanup import ReportCleanupService
from app.services.images import ValidatedImage
from app.services.reports import ReportService
from app.services.storage import ImageStorage, StoredImage


class FakeStorage(ImageStorage):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def save(self, data: bytes, mime_type: str, extension: str) -> StoredImage:
        key = f"issues/test{extension}"
        self.files[key] = data
        return StoredImage(key=key, mime_type=mime_type)

    def read(self, key: str) -> bytes:
        return self.files[key]

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.files.pop(key, None)

    def list_keys(self, prefix: str = "issues/", limit: int = 500) -> list[str]:
        return [key for key in sorted(self.files) if key.startswith(prefix)][:limit]

    def health_check(self) -> None:
        return None


class FakeAnalyzer(CivicIssueAnalyzer):
    model_name = "fake-gemini"

    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis:
        assert not hasattr(report, "citizen_contact")
        assert image_bytes == b"image"
        assert image_mime == "image/png"
        return AIAnalysis(
            title="Severe pothole near school gate",
            ai_summary=(
                "A large pothole near the school gate creates a safety risk for local traffic."
            ),
            category=IssueCategory.ROAD_DAMAGE,
            severity=IssueSeverity.HIGH,
            urgency_level=UrgencyLevel.URGENT,
            urgency_reason="Children and two-wheel riders use this road every day.",
            suggested_department="Public Works / Road Maintenance",
            safety_risk="Riders may lose control and pedestrians may trip.",
            citizen_explanation="Review these details before publishing the public issue.",
            suggested_next_action="Publish the issue for community verification.",
        )


class FailingAnalyzer(FakeAnalyzer):
    def analyze(
        self,
        report: AIReportInput,
        image_bytes: bytes,
        image_mime: str,
    ) -> AIAnalysis:
        del report, image_bytes, image_mime
        raise AppError(code="ai_unavailable", message="Try again", status_code=503)


class FakeReportRepository(ReportRepository):
    def __init__(self) -> None:
        self.drafts: dict[uuid.UUID, IssueDraft] = {}
        self.issues: dict[str, Issue] = {}
        self.areas: dict[str, Area] = {}

    def add_draft(self, draft: IssueDraft) -> IssueDraft:
        draft.id = draft.id or uuid.uuid4()
        draft.created_at = datetime.now(UTC)
        draft.updated_at = draft.created_at
        self.drafts[draft.id] = draft
        return draft

    def get_draft(self, draft_id: uuid.UUID, *, for_update: bool = False) -> IssueDraft | None:
        del for_update
        return self.drafts.get(draft_id)

    def delete_draft(self, draft: IssueDraft) -> None:
        self.drafts.pop(draft.id, None)

    def add_issue(self, issue: Issue) -> Issue:
        issue.id = issue.id or uuid.uuid4()
        issue.created_at = datetime.now(UTC)
        issue.updated_at = issue.created_at
        if issue.area is not None:
            issue.area_id = issue.area.id
        self.issues[issue.image_key] = issue
        return issue

    def get_or_create_area_for_location(self, location: str) -> Area:
        area = self.areas.get(location)
        if area is None:
            area = Area(
                id=uuid.uuid4(),
                name=location,
                slug=location.lower().replace(" ", "-"),
                city="CivicPulse City",
                overall_score=70,
                infrastructure_score=70,
                cleanliness_score=70,
                safety_score=70,
                participation_score=70,
                responsiveness_score=70,
                environment_score=70,
                status_label="improving",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self.areas[location] = area
        return area

    def find_issue_by_image_key(self, image_key: str) -> Issue | None:
        return self.issues.get(image_key)

    def expired_unpublished_drafts(
        self,
        cutoff: datetime,
        *,
        limit: int,
    ) -> list[IssueDraft]:
        return [
            draft
            for draft in sorted(self.drafts.values(), key=lambda item: item.expires_at)
            if draft.published_at is None and draft.expires_at <= cutoff
        ][:limit]

    def existing_image_keys(self, image_keys: set[str]) -> set[str]:
        draft_keys = {draft.image_key for draft in self.drafts.values()}
        issue_keys = set(self.issues)
        return image_keys & (draft_keys | issue_keys)

    def flush(self) -> None:
        return None


class FakeAreaScoreTrigger:
    def __init__(self) -> None:
        self.calls: list[tuple[uuid.UUID, uuid.UUID | None, str]] = []

    def recalculate_issue_area(self, issue: Issue, *, event_type: str) -> None:
        self.calls.append((issue.id, issue.area_id, event_type))


@pytest.fixture
def report_input() -> ReportAnalysisInput:
    return ReportAnalysisInput(
        original_description=(
            "There is a huge pothole near the school gate and bikes are slipping."
        ),
        location="Sector 12",
        landmark="City Public School",
        latitude=26.9124,
        longitude=75.7873,
        citizen_name="Citizen",
        citizen_contact="private@example.com",
        urgency_note="Children cross here every morning.",
    )


@pytest.fixture
def image() -> ValidatedImage:
    return ValidatedImage(
        data=b"image",
        mime_type="image/png",
        extension=".png",
        width=8,
        height=8,
    )


def build_service(
    repository: FakeReportRepository | None = None,
    storage: FakeStorage | None = None,
    analyzer: CivicIssueAnalyzer | None = None,
    area_score_trigger: FakeAreaScoreTrigger | None = None,
) -> tuple[ReportService, FakeReportRepository, FakeStorage]:
    repo = repository or FakeReportRepository()
    image_storage = storage or FakeStorage()
    service = ReportService(
        repository=repo,
        storage=image_storage,
        analyzer=analyzer or FakeAnalyzer(),
        settings=Settings(report_draft_ttl_minutes=60),
        area_score_trigger=area_score_trigger,
    )
    return service, repo, image_storage


def test_analyze_edit_publish_and_repeat_are_idempotent(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    service, repository, _storage = build_service()

    draft = service.analyze(report_input, image)
    edited = service.update_draft(
        draft.id,
        ReportDraftUpdate(title="Edited pothole report near school gate"),
    )
    first = service.publish(draft.id)
    second = service.publish(draft.id)

    assert edited.title == "Edited pothole report near school gate"
    assert first.issue_id == second.issue_id
    assert first.status is IssueStatus.REPORTED
    assert len(repository.issues) == 1
    issue = next(iter(repository.issues.values()))
    assert issue.citizen_contact == "private@example.com"
    assert issue.latitude == 26.9124
    assert issue.longitude == 75.7873
    assert issue.area is not None
    assert issue.area.name == "Sector 12"
    assert len(issue.updates) == 1


def test_draft_response_exposes_coordinates(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    service, _repository, _storage = build_service()

    draft = service.analyze(report_input, image)
    fetched = service.get_draft(draft.id)

    assert draft.latitude == 26.9124
    assert draft.longitude == 75.7873
    assert fetched.latitude == 26.9124
    assert fetched.longitude == 75.7873


def test_publish_triggers_civic_genome_recalculation_once(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    trigger = FakeAreaScoreTrigger()
    service, repository, _storage = build_service(area_score_trigger=trigger)
    draft = service.analyze(report_input, image)

    first = service.publish(draft.id)
    second = service.publish(draft.id)

    assert first.issue_id == second.issue_id
    assert trigger.calls == [
        (first.issue_id, next(iter(repository.issues.values())).area_id, "issue_published"),
    ]


def test_ai_failure_removes_uploaded_image(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    storage = FakeStorage()
    service, repository, _storage = build_service(
        storage=storage,
        analyzer=FailingAnalyzer(),
    )

    with pytest.raises(AppError):
        service.analyze(report_input, image)

    assert repository.drafts == {}
    assert storage.deleted == ["issues/test.png"]


def test_expired_draft_cannot_publish(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    service, repository, _storage = build_service()
    draft = service.analyze(report_input, image)
    repository.drafts[draft.id].expires_at = datetime.now(UTC) - timedelta(seconds=1)

    with pytest.raises(AppError) as caught:
        service.publish(draft.id)

    assert caught.value.code == "draft_expired"
    assert repository.issues == {}


def test_cancel_removes_draft_and_image(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    service, repository, storage = build_service()
    draft = service.analyze(report_input, image)

    service.cancel(draft.id)

    assert draft.id not in repository.drafts
    assert storage.deleted == ["issues/test.png"]


def test_cleanup_removes_expired_unpublished_drafts_and_images(
    report_input: ReportAnalysisInput,
    image: ValidatedImage,
) -> None:
    service, repository, storage = build_service()
    expired = service.analyze(report_input, image)
    repository.drafts[expired.id].expires_at = datetime.now(UTC) - timedelta(minutes=5)

    result = ReportCleanupService(repository, storage).cleanup_abandoned_drafts()

    assert result.abandoned_drafts == 1
    assert result.abandoned_images == 1
    assert repository.drafts == {}
    assert storage.deleted == ["issues/test.png"]


def test_cleanup_removes_unused_images_but_keeps_referenced_images() -> None:
    repository = FakeReportRepository()
    storage = FakeStorage()
    storage.files = {
        "issues/referenced.png": b"keep",
        "issues/orphan.png": b"remove",
    }
    repository.issues["issues/referenced.png"] = Issue(
        id=uuid.uuid4(),
        public_reference="CP-20260625-ABCDEF12",
        title="Referenced issue image",
        original_description="A referenced public issue.",
        ai_summary="A referenced public issue summary.",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.MEDIUM,
        urgency_level=UrgencyLevel.SOON,
        urgency_reason="Routine maintenance should inspect it.",
        suggested_department="Public Works",
        safety_risk="Use caution nearby.",
        citizen_explanation="The issue is published.",
        suggested_next_action="Track the issue publicly.",
        location="Sector 12",
        landmark=None,
        image_key="issues/referenced.png",
        image_mime="image/png",
        status=IssueStatus.REPORTED,
        citizen_name=None,
        citizen_contact=None,
        ai_model="test",
        prompt_version="test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    result = ReportCleanupService(repository, storage).cleanup_unused_images()

    assert result.unused_images == 1
    assert "issues/referenced.png" in storage.files
    assert "issues/orphan.png" not in storage.files
