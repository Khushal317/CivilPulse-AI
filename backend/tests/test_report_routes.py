from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from PIL import Image

from app.api.dependencies import get_report_analysis_rate_limiter, get_report_service
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus, UrgencyLevel
from app.main import app
from app.schemas.issues import (
    PublishedReportResponse,
    ReportAnalysisInput,
    ReportDraftResponse,
    ReportDraftUpdate,
)


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (8, 8), color=(20, 80, 120)).save(output, format="PNG")
    return output.getvalue()


class FakeRouteReportService:
    def __init__(self) -> None:
        self.analyze_calls = 0
        self.draft_id = uuid4()
        self.last_report: ReportAnalysisInput | None = None

    def response(self) -> ReportDraftResponse:
        return ReportDraftResponse(
            id=self.draft_id,
            title="Pothole near school gate",
            original_description="A large pothole is making bikes slip near the school.",
            ai_summary="A large pothole creates a road safety risk near a school entrance.",
            category=IssueCategory.ROAD_DAMAGE,
            severity=IssueSeverity.HIGH,
            urgency_level=UrgencyLevel.URGENT,
            urgency_reason="Children and riders use this road every day.",
            suggested_department="Public Works",
            safety_risk="Riders may lose control.",
            citizen_explanation="Review the structured complaint before publishing.",
            suggested_next_action="Publish for community verification.",
            location="Sector 12",
            landmark="City Public School",
            ai_model="gemini-test",
            latitude=26.9124,
            longitude=75.7873,
            urgency_note=None,
            image_url="/api/v1/media/issues/test.png",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            created_at=datetime.now(UTC),
        )

    def analyze(self, report: ReportAnalysisInput, image: object) -> ReportDraftResponse:
        del image
        self.last_report = report
        self.analyze_calls += 1
        return self.response()

    def get_draft(self, draft_id: UUID) -> ReportDraftResponse:
        assert draft_id == self.draft_id
        return self.response()

    def update_draft(
        self,
        draft_id: UUID,
        changes: ReportDraftUpdate,
    ) -> ReportDraftResponse:
        assert draft_id == self.draft_id
        response = self.response()
        return response.model_copy(update=changes.model_dump(exclude_unset=True))

    def publish(self, draft_id: UUID) -> PublishedReportResponse:
        assert draft_id == self.draft_id
        return PublishedReportResponse(
            issue_id=uuid4(),
            public_reference="CP-20260625-1234ABCD",
            status=IssueStatus.REPORTED,
            published_at=datetime.now(UTC),
        )

    def cancel(self, draft_id: UUID) -> None:
        assert draft_id == self.draft_id


class AlwaysLimitedRateLimiter:
    def hit(self, key: str) -> None:
        del key
        raise AppError(
            code="report_analysis_rate_limited",
            message="Too many report analyses were requested. Please try again later.",
            status_code=429,
        )


def test_invalid_image_is_rejected_before_report_service(client: TestClient) -> None:
    service = FakeRouteReportService()
    app.dependency_overrides[get_report_service] = lambda: service

    response = client.post(
        "/api/v1/reports/analyze",
        data={
            "original_description": "There is a dangerous pothole near the school.",
            "location": "Sector 12",
            "latitude": "26.9124",
            "longitude": "75.7873",
        },
        files={"image": ("issue.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_image"
    assert service.analyze_calls == 0


def test_report_analysis_rate_limit_runs_before_analysis(client: TestClient) -> None:
    service = FakeRouteReportService()
    app.dependency_overrides[get_report_service] = lambda: service
    app.dependency_overrides[get_report_analysis_rate_limiter] = lambda: AlwaysLimitedRateLimiter()

    response = client.post(
        "/api/v1/reports/analyze",
        data={
            "original_description": "There is a dangerous pothole near the school.",
            "location": "Sector 12",
            "latitude": "26.9124",
            "longitude": "75.7873",
        },
        files={"image": ("issue.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "report_analysis_rate_limited"
    assert service.analyze_calls == 0


def test_report_route_lifecycle(client: TestClient) -> None:
    service = FakeRouteReportService()
    app.dependency_overrides[get_report_service] = lambda: service

    analyzed = client.post(
        "/api/v1/reports/analyze",
        data={
            "original_description": "There is a dangerous pothole near the school.",
            "location": "Sector 12",
            "latitude": "26.9124",
            "longitude": "75.7873",
        },
        files={"image": ("issue.png", png_bytes(), "image/png")},
    )
    draft_id = analyzed.json()["id"]
    updated = client.patch(
        f"/api/v1/reports/{draft_id}",
        json={"title": "Edited civic issue title"},
    )
    published = client.post(f"/api/v1/reports/{draft_id}/publish")
    cancelled = client.delete(f"/api/v1/reports/{draft_id}")

    assert analyzed.status_code == 201
    assert analyzed.json()["latitude"] == 26.9124
    assert analyzed.json()["longitude"] == 75.7873
    assert service.last_report is not None
    assert service.last_report.latitude == 26.9124
    assert service.last_report.longitude == 75.7873
    assert updated.json()["title"] == "Edited civic issue title"
    assert published.json()["status"] == "reported"
    assert cancelled.status_code == 204


def test_report_route_rejects_half_coordinate_pair(client: TestClient) -> None:
    service = FakeRouteReportService()
    app.dependency_overrides[get_report_service] = lambda: service

    response = client.post(
        "/api/v1/reports/analyze",
        data={
            "original_description": "There is a dangerous pothole near the school.",
            "location": "Sector 12",
            "latitude": "26.9124",
        },
        files={"image": ("issue.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert service.analyze_calls == 0
