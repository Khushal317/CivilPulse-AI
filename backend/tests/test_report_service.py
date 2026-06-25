import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus, UrgencyLevel
from app.models.issue import Issue
from app.models.issue_draft import IssueDraft
from app.repositories.reports import ReportRepository
from app.schemas.issues import AIAnalysis, AIReportInput, ReportAnalysisInput, ReportDraftUpdate
from app.services.ai import CivicIssueAnalyzer
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
        self.issues[issue.image_key] = issue
        return issue

    def find_issue_by_image_key(self, image_key: str) -> Issue | None:
        return self.issues.get(image_key)

    def flush(self) -> None:
        return None


@pytest.fixture
def report_input() -> ReportAnalysisInput:
    return ReportAnalysisInput(
        original_description=(
            "There is a huge pothole near the school gate and bikes are slipping."
        ),
        location="Sector 12",
        landmark="City Public School",
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
) -> tuple[ReportService, FakeReportRepository, FakeStorage]:
    repo = repository or FakeReportRepository()
    image_storage = storage or FakeStorage()
    service = ReportService(
        repository=repo,
        storage=image_storage,
        analyzer=analyzer or FakeAnalyzer(),
        settings=Settings(report_draft_ttl_minutes=60),
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
    assert len(issue.updates) == 1


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
