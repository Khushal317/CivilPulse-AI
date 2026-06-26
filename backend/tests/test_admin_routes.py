from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_admin_auth_service,
    get_admin_service,
    get_operations_service,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.main import app
from app.models.admin_session import AdminSession
from app.repositories.admin import AdminSessionRepository
from app.schemas.admin import (
    AdminDashboardMetrics,
    AdminDashboardResponse,
    AdminIssueDetail,
    AdminIssueListQuery,
    AdminIssueListResponse,
    AdminIssueSummary,
    AdminStatusUpdateRequest,
    CategoryMetric,
)
from app.schemas.issues import CommunityCounts
from app.schemas.operations import OperationsReportResponse
from app.services.admin_auth import AdminAuthService, LoginRateLimiter
from app.services.passwords import hash_password


class RouteSessionRepository(AdminSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[str, AdminSession] = {}

    def add(self, session: AdminSession) -> AdminSession:
        session.id = uuid4()
        session.created_at = datetime.now(UTC)
        self.sessions[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash: str) -> AdminSession | None:
        return self.sessions.get(token_hash)

    def revoke(self, session: AdminSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at

    def flush(self) -> None:
        return None


def summary() -> AdminIssueSummary:
    return AdminIssueSummary(
        id=UUID(int=1),
        public_reference="CP-20260625-00000001",
        title="Pothole near school",
        category=IssueCategory.ROAD_DAMAGE,
        severity=IssueSeverity.HIGH,
        status=IssueStatus.REPORTED,
        location="Sector 12",
        landmark="City School",
        created_at=datetime(2026, 6, 25, tzinfo=UTC),
        updated_at=datetime(2026, 6, 25, tzinfo=UTC),
        verification_count=3,
    )


def detail(status: IssueStatus = IssueStatus.REPORTED) -> AdminIssueDetail:
    return AdminIssueDetail(
        **summary().model_dump(exclude={"status"}),
        status=status,
        original_description="A resident reported a pothole near a school.",
        ai_summary="A road defect creates a public safety risk.",
        urgency_level="urgent",
        urgency_reason="Children use this road.",
        suggested_department="Public Works",
        safety_risk="Riders may lose control.",
        citizen_explanation="Administrator review is needed.",
        suggested_next_action="Arrange an inspection.",
        image_url="/api/v1/media/issues/one.jpg",
        image_mime="image/jpeg",
        citizen_name="Private Citizen",
        citizen_contact="private@example.com",
        ai_model="gemini-test",
        prompt_version="v1",
        community_counts=CommunityCounts(saw_this_too=3),
        updates=[],
    )


class FakeRouteAdminService:
    def dashboard(self) -> AdminDashboardResponse:
        return AdminDashboardResponse(
            metrics=AdminDashboardMetrics(
                total_reports=1,
                high_severity=1,
                verified=0,
                pending=1,
                resolved=0,
            ),
            category_breakdown=[CategoryMetric(category=IssueCategory.ROAD_DAMAGE, count=1)],
            latest_reports=[summary()],
            priority_issues=[summary()],
        )

    def list_issues(self, query: AdminIssueListQuery) -> AdminIssueListResponse:
        return AdminIssueListResponse(
            items=[summary()],
            page=query.page,
            page_size=query.page_size,
            total_items=1,
            total_pages=1,
        )

    def get_issue(self, issue_id: UUID) -> AdminIssueDetail:
        assert issue_id == UUID(int=1)
        return detail()

    def update_status(
        self,
        issue_id: UUID,
        request: AdminStatusUpdateRequest,
    ) -> AdminIssueDetail:
        assert issue_id == UUID(int=1)
        return detail(request.to_status)


def operations_report() -> OperationsReportResponse:
    return OperationsReportResponse(
        id=UUID(int=10),
        generated_at=datetime(2026, 6, 26, 10, tzinfo=UTC),
        created_at=datetime(2026, 6, 26, 10, tzinfo=UTC),
        total_issues_analyzed=1,
        model_used="demo-civic-operations-agent-v1",
        executive_summary="One active issue needs administrator review.",
        urgent_issues=[],
        duplicate_clusters=[],
        area_hotspots=[
            {
                "area": "Sector 12",
                "issue_count": 1,
                "main_categories": ["road_damage"],
                "risk_level": "medium",
                "insight": "Sector 12 has one active issue.",
            },
        ],
        department_priorities=[],
        escalation_messages=[],
        predicted_risks=[],
        raw_response={"executive_summary": "One active issue needs administrator review."},
    )


class FakeRouteOperationsService:
    def __init__(
        self,
        *,
        latest: OperationsReportResponse | None = None,
        fail_analysis: bool = False,
    ) -> None:
        self.latest = latest
        self.fail_analysis = fail_analysis
        self.analyze_calls = 0
        self.latest_calls = 0
        self.saved_reports = 0

    def analyze_active_issues(self) -> OperationsReportResponse:
        self.analyze_calls += 1
        if self.fail_analysis:
            raise AppError(
                code="operations_ai_unavailable",
                message="The Civic Operations Agent could not analyze city issues right now.",
                status_code=503,
            )
        self.saved_reports += 1
        self.latest = operations_report()
        return self.latest

    def latest_report(self) -> OperationsReportResponse | None:
        self.latest_calls += 1
        return self.latest


def configure_admin_overrides(
    operations_service: FakeRouteOperationsService | None = None,
) -> AdminAuthService:
    auth = AdminAuthService(
        repository=RouteSessionRepository(),
        settings=Settings(
            admin_username="admin",
            admin_password_hash=hash_password("route-password"),
            admin_session_secret="route-secret",
        ),
        rate_limiter=LoginRateLimiter(5, 15),
    )
    app.dependency_overrides[get_admin_auth_service] = lambda: auth
    app.dependency_overrides[get_admin_service] = lambda: FakeRouteAdminService()
    app.dependency_overrides[get_operations_service] = (
        lambda: operations_service or FakeRouteOperationsService()
    )
    return auth


def test_anonymous_admin_access_and_invalid_credentials_are_rejected(
    client: TestClient,
) -> None:
    configure_admin_overrides()

    anonymous = client.get("/api/v1/admin/dashboard")
    invalid = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "wrong"},
    )

    assert anonymous.status_code == 401
    assert invalid.status_code == 401
    assert "civicpulse_admin_session" not in invalid.cookies


def test_login_session_protected_data_csrf_update_and_logout(
    client: TestClient,
) -> None:
    configure_admin_overrides()

    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]
    current = client.get("/api/v1/admin/auth/session")
    dashboard = client.get("/api/v1/admin/dashboard")
    missing_csrf = client.post(
        f"/api/v1/admin/issues/{UUID(int=1)}/status",
        json={"to_status": "in_progress", "note": "Inspection assigned."},
    )
    updated = client.post(
        f"/api/v1/admin/issues/{UUID(int=1)}/status",
        headers={"X-CSRF-Token": csrf},
        json={"to_status": "in_progress", "note": "Inspection assigned."},
    )
    logout = client.post(
        "/api/v1/admin/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )
    after_logout = client.get("/api/v1/admin/dashboard")

    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert "SameSite=strict" in login.headers["set-cookie"]
    assert current.status_code == 200
    assert dashboard.json()["metrics"]["total_reports"] == 1
    assert missing_csrf.status_code == 403
    assert updated.json()["status"] == "in_progress"
    assert logout.status_code == 204
    assert after_logout.status_code == 401


def test_admin_operations_endpoints_require_admin_and_csrf(
    client: TestClient,
) -> None:
    configure_admin_overrides()

    anonymous_latest = client.get("/api/v1/admin/operations/latest")
    anonymous_analyze = client.post("/api/v1/admin/operations/analyze")

    assert anonymous_latest.status_code == 401
    assert anonymous_analyze.status_code == 401


def test_admin_can_generate_and_fetch_operations_report(
    client: TestClient,
) -> None:
    operations_service = FakeRouteOperationsService(latest=operations_report())
    configure_admin_overrides(operations_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]

    latest = client.get("/api/v1/admin/operations/latest")
    missing_csrf = client.post("/api/v1/admin/operations/analyze")
    generated = client.post(
        "/api/v1/admin/operations/analyze",
        headers={"X-CSRF-Token": csrf},
    )
    latest_after = client.get("/api/v1/admin/operations/latest")

    assert latest.status_code == 200
    assert latest.json()["id"] == str(UUID(int=10))
    assert missing_csrf.status_code == 403
    assert generated.status_code == 200
    assert generated.json()["model_used"] == "demo-civic-operations-agent-v1"
    assert latest_after.json()["total_issues_analyzed"] == 1
    assert operations_service.analyze_calls == 1
    assert operations_service.latest_calls == 2
    assert operations_service.saved_reports == 1


def test_admin_latest_operations_report_can_be_empty(
    client: TestClient,
) -> None:
    configure_admin_overrides(FakeRouteOperationsService(latest=None))
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    assert login.status_code == 200

    latest = client.get("/api/v1/admin/operations/latest")

    assert latest.status_code == 200
    assert latest.json() is None


def test_failed_operations_analysis_returns_safe_error_without_partial_save(
    client: TestClient,
) -> None:
    operations_service = FakeRouteOperationsService(fail_analysis=True)
    configure_admin_overrides(operations_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )

    failed = client.post(
        "/api/v1/admin/operations/analyze",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
    )

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "operations_ai_unavailable"
    assert operations_service.analyze_calls == 1
    assert operations_service.saved_reports == 0
