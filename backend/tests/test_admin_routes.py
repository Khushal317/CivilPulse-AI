from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_admin_auth_service,
    get_admin_service,
    get_mission_generation_service,
    get_mission_refinement_service,
    get_mission_service,
    get_operations_service,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.domain.missions import MissionStatus, MissionType
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
    DuplicateIssueResolutionRequest,
    DuplicateIssueResolutionResponse,
)
from app.schemas.issues import CommunityCounts
from app.schemas.missions import (
    AdminMissionListResponse,
    ManualMissionCreate,
    ManualMissionDraft,
    MissionAreaSummary,
    MissionDetail,
    MissionGenerationResponse,
    MissionSummary,
)
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
    def __init__(self) -> None:
        self.duplicate_requests: list[DuplicateIssueResolutionRequest] = []

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

    def mark_duplicates(
        self,
        request: DuplicateIssueResolutionRequest,
    ) -> DuplicateIssueResolutionResponse:
        self.duplicate_requests.append(request)
        duplicate = summary().model_copy(
            update={
                "id": request.duplicate_issue_ids[0],
                "public_reference": "CP-20260625-00000002",
                "title": "Road crater near school",
                "status": IssueStatus.DUPLICATE,
            },
        )
        return DuplicateIssueResolutionResponse(
            canonical_issue=summary(),
            duplicates_marked=[duplicate],
        )


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


def mission_generation_response() -> MissionGenerationResponse:
    now = datetime(2026, 6, 27, 10, tzinfo=UTC)
    area = MissionAreaSummary(
        id=UUID(int=30),
        name="Sector 12",
        slug="civicpulse-city-sector-12",
        city="CivicPulse City",
    )
    mission = MissionDetail(
        **MissionSummary(
            id=UUID(int=31),
            title="Verify Sector 12 streetlights",
            mission_type=MissionType.VERIFICATION,
            status=MissionStatus.DRAFT,
            area=area,
            goal_description="Ask residents to safely confirm public streetlights are working.",
            target_count=5,
            progress_count=0,
            category=IssueCategory.STREETLIGHT,
            reward={"points": 20, "score_key": "participation"},
            ai_reason="A verified streetlight report needs additional safe observations.",
            expires_at=now,
            published_at=None,
            completed_at=None,
            created_at=now,
            updated_at=now,
        ).model_dump(),
        linked_issue_ids=[UUID(int=1)],
    )
    return MissionGenerationResponse(
        model_used="demo-civic-mission-generator-v1",
        created_drafts=[mission],
    )


def route_mission(
    *,
    mission_id: UUID | None = None,
    status: MissionStatus = MissionStatus.DRAFT,
) -> MissionDetail:
    now = datetime(2026, 6, 27, 10, tzinfo=UTC)
    selected_mission_id = mission_id or UUID(int=31)
    area = MissionAreaSummary(
        id=UUID(int=30),
        name="Sector 12",
        slug="civicpulse-city-sector-12",
        city="CivicPulse City",
    )
    return MissionDetail(
        **MissionSummary(
            id=selected_mission_id,
            title="Verify Sector 12 streetlights",
            mission_type=MissionType.VERIFICATION,
            status=status,
            area=area,
            goal_description="Ask residents to safely confirm public streetlights are working.",
            target_count=5,
            progress_count=5 if status is MissionStatus.COMPLETED else 0,
            category=IssueCategory.STREETLIGHT,
            reward={"points": 20, "score_key": "participation"},
            ai_reason="A verified streetlight report needs additional safe observations.",
            expires_at=now,
            published_at=None if status is MissionStatus.DRAFT else now,
            completed_at=now if status is MissionStatus.COMPLETED else None,
            created_at=now,
            updated_at=now,
        ).model_dump(),
        linked_issue_ids=[UUID(int=1)],
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


class FakeRouteMissionGenerationService:
    def __init__(self, *, fail_generation: bool = False) -> None:
        self.fail_generation = fail_generation
        self.generate_calls = 0
        self.saved_drafts = 0

    def generate_drafts(self) -> MissionGenerationResponse:
        self.generate_calls += 1
        if self.fail_generation:
            raise AppError(
                code="mission_ai_unavailable",
                message="The Civic Mission Generator could not create missions right now.",
                status_code=503,
            )
        self.saved_drafts += 1
        return mission_generation_response()


class FakeRouteMissionService:
    def __init__(self) -> None:
        self.list_calls = 0
        self.published: list[UUID] = []
        self.expired: list[UUID] = []
        self.completed: list[UUID] = []
        self.deleted: list[UUID] = []
        self.created: list[ManualMissionCreate] = []

    def list_admin(self) -> AdminMissionListResponse:
        self.list_calls += 1
        return AdminMissionListResponse(
            drafts=[route_mission(status=MissionStatus.DRAFT)],
            active=[route_mission(mission_id=UUID(int=32), status=MissionStatus.ACTIVE)],
            completed=[route_mission(mission_id=UUID(int=33), status=MissionStatus.COMPLETED)],
            expired=[route_mission(mission_id=UUID(int=34), status=MissionStatus.EXPIRED)],
        )

    def publish(self, mission_id: UUID) -> MissionDetail:
        self.published.append(mission_id)
        return route_mission(mission_id=mission_id, status=MissionStatus.ACTIVE)

    def expire(self, mission_id: UUID) -> MissionDetail:
        self.expired.append(mission_id)
        return route_mission(mission_id=mission_id, status=MissionStatus.EXPIRED)

    def complete(self, mission_id: UUID) -> MissionDetail:
        self.completed.append(mission_id)
        return route_mission(mission_id=mission_id, status=MissionStatus.COMPLETED)

    def delete(self, mission_id: UUID) -> None:
        self.deleted.append(mission_id)

    def create_manual(self, mission: ManualMissionCreate) -> MissionDetail:
        self.created.append(mission)
        return route_mission(
            mission_id=UUID(int=35),
            status=MissionStatus.ACTIVE if mission.publish else MissionStatus.DRAFT,
        )


class FakeRouteMissionRefinementService:
    def __init__(self) -> None:
        self.refined: list[ManualMissionDraft] = []

    def refine(self, draft: ManualMissionDraft) -> ManualMissionDraft:
        self.refined.append(draft)
        return draft.model_copy(
            update={
                "title": f"Verify {draft.title}",
                "goal_description": (
                    f"{draft.goal_description.rstrip('.')} with safe public observations."
                ),
            },
        )


def configure_admin_overrides(
    operations_service: FakeRouteOperationsService | None = None,
    mission_generation_service: FakeRouteMissionGenerationService | None = None,
    mission_service: FakeRouteMissionService | None = None,
    mission_refinement_service: FakeRouteMissionRefinementService | None = None,
    admin_service: FakeRouteAdminService | None = None,
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
    app.dependency_overrides[get_admin_service] = lambda: admin_service or FakeRouteAdminService()
    app.dependency_overrides[get_operations_service] = (
        lambda: operations_service or FakeRouteOperationsService()
    )
    app.dependency_overrides[get_mission_generation_service] = (
        lambda: mission_generation_service or FakeRouteMissionGenerationService()
    )
    app.dependency_overrides[get_mission_service] = (
        lambda: mission_service or FakeRouteMissionService()
    )
    app.dependency_overrides[get_mission_refinement_service] = (
        lambda: mission_refinement_service or FakeRouteMissionRefinementService()
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


def test_admin_can_mark_duplicate_issues_with_csrf(client: TestClient) -> None:
    admin_service = FakeRouteAdminService()
    configure_admin_overrides(admin_service=admin_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]

    missing_csrf = client.post(
        "/api/v1/admin/issues/duplicates",
        json={
            "canonical_issue_id": str(UUID(int=1)),
            "duplicate_issue_ids": [str(UUID(int=2))],
            "reason": "Both reports describe the same road damage.",
        },
    )
    resolved = client.post(
        "/api/v1/admin/issues/duplicates",
        headers={"X-CSRF-Token": csrf},
        json={
            "canonical_issue_id": str(UUID(int=1)),
            "duplicate_issue_ids": [str(UUID(int=2))],
            "reason": "Both reports describe the same road damage.",
        },
    )

    assert missing_csrf.status_code == 403
    assert resolved.status_code == 200
    assert resolved.json()["canonical_issue"]["id"] == str(UUID(int=1))
    assert resolved.json()["duplicates_marked"][0]["status"] == "duplicate"
    assert admin_service.duplicate_requests[0].canonical_issue_id == UUID(int=1)


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


def test_admin_can_generate_mission_drafts(
    client: TestClient,
) -> None:
    mission_service = FakeRouteMissionGenerationService()
    configure_admin_overrides(mission_generation_service=mission_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]

    missing_csrf = client.post("/api/v1/admin/missions/generate")
    generated = client.post(
        "/api/v1/admin/missions/generate",
        headers={"X-CSRF-Token": csrf},
    )

    assert missing_csrf.status_code == 403
    assert generated.status_code == 200
    body = generated.json()
    assert body["model_used"] == "demo-civic-mission-generator-v1"
    assert body["created_drafts"][0]["status"] == "draft"
    assert body["created_drafts"][0]["published_at"] is None
    assert mission_service.generate_calls == 1
    assert mission_service.saved_drafts == 1


def test_failed_mission_generation_returns_safe_error_without_partial_save(
    client: TestClient,
) -> None:
    mission_service = FakeRouteMissionGenerationService(fail_generation=True)
    configure_admin_overrides(mission_generation_service=mission_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )

    failed = client.post(
        "/api/v1/admin/missions/generate",
        headers={"X-CSRF-Token": login.json()["csrf_token"]},
    )

    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "mission_ai_unavailable"
    assert mission_service.generate_calls == 1
    assert mission_service.saved_drafts == 0


def test_admin_mission_console_requires_admin_and_csrf(client: TestClient) -> None:
    configure_admin_overrides()

    anonymous_list = client.get("/api/v1/admin/missions")
    anonymous_publish = client.post(
        f"/api/v1/admin/missions/{UUID(int=31)}/publish",
    )

    assert anonymous_list.status_code == 401
    assert anonymous_publish.status_code == 401


def test_admin_can_list_and_manage_missions(client: TestClient) -> None:
    mission_service = FakeRouteMissionService()
    configure_admin_overrides(mission_service=mission_service)
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]

    listed = client.get("/api/v1/admin/missions")
    missing_csrf = client.post(f"/api/v1/admin/missions/{UUID(int=31)}/publish")
    published = client.post(
        f"/api/v1/admin/missions/{UUID(int=31)}/publish",
        headers={"X-CSRF-Token": csrf},
    )
    expired = client.post(
        f"/api/v1/admin/missions/{UUID(int=32)}/expire",
        headers={"X-CSRF-Token": csrf},
    )
    completed = client.post(
        f"/api/v1/admin/missions/{UUID(int=32)}/complete",
        headers={"X-CSRF-Token": csrf},
    )
    deleted = client.delete(
        f"/api/v1/admin/missions/{UUID(int=31)}",
        headers={"X-CSRF-Token": csrf},
    )

    assert listed.status_code == 200
    assert listed.json()["drafts"][0]["status"] == "draft"
    assert listed.json()["active"][0]["status"] == "active"
    assert listed.json()["completed"][0]["status"] == "completed"
    assert listed.json()["expired"][0]["status"] == "expired"
    assert missing_csrf.status_code == 403
    assert published.json()["status"] == "active"
    assert expired.json()["status"] == "expired"
    assert completed.json()["status"] == "completed"
    assert deleted.status_code == 204
    assert mission_service.published == [UUID(int=31)]
    assert mission_service.expired == [UUID(int=32)]
    assert mission_service.completed == [UUID(int=32)]
    assert mission_service.deleted == [UUID(int=31)]


def test_admin_can_create_and_refine_manual_missions(client: TestClient) -> None:
    mission_service = FakeRouteMissionService()
    refinement_service = FakeRouteMissionRefinementService()
    configure_admin_overrides(
        mission_service=mission_service,
        mission_refinement_service=refinement_service,
    )
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": "route-password"},
    )
    csrf = login.json()["csrf_token"]
    payload = {
        "title": "Road damage near DMART",
        "area_id": str(UUID(int=1)),
        "mission_type": "verification",
        "goal_description": "Ask residents to safely verify the visible road damage.",
        "target_count": 3,
        "category": "road_damage",
        "reward_points": 20,
        "reward_score_key": "participation",
        "ai_reason": "This mission helps gather safe public confirmation before follow-up.",
        "linked_issue_ids": [],
        "expires_in_days": 7,
    }

    missing_csrf = client.post("/api/v1/admin/missions/manual", json=payload | {"publish": True})
    refined = client.post(
        "/api/v1/admin/missions/manual/refine",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )
    created = client.post(
        "/api/v1/admin/missions/manual",
        headers={"X-CSRF-Token": csrf},
        json=payload | {"publish": True},
    )

    assert missing_csrf.status_code == 403
    assert refined.status_code == 200
    assert refined.json()["title"] == "Verify Road damage near DMART"
    assert created.status_code == 200
    assert created.json()["status"] == "active"
    assert refinement_service.refined[0].title == "Road damage near DMART"
    assert mission_service.created[0].publish is True
