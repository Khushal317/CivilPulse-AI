from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, Query, Request, Response, status

from app.api.dependencies import (
    AdminAuthServiceDependency,
    AdminServiceDependency,
    MissionGenerationServiceDependency,
    MissionRefinementServiceDependency,
    MissionServiceDependency,
    OperationsServiceDependency,
    SettingsDependency,
)
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminIssueDetail,
    AdminIssueListQuery,
    AdminIssueListResponse,
    AdminLoginRequest,
    AdminSessionResponse,
    AdminStatusUpdateRequest,
    DuplicateIssueResolutionRequest,
    DuplicateIssueResolutionResponse,
)
from app.schemas.missions import (
    AdminMissionListResponse,
    ManualMissionCreate,
    ManualMissionDraft,
    MissionDetail,
    MissionGenerationResponse,
)
from app.schemas.operations import OperationsReportResponse
from app.services.admin_auth import ADMIN_COOKIE_NAME, AuthenticatedAdmin

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(
    service: AdminAuthServiceDependency,
    raw_token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE_NAME)] = None,
) -> AuthenticatedAdmin:
    return service.authenticate(raw_token)


def require_admin_csrf(
    service: AdminAuthServiceDependency,
    raw_token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE_NAME)] = None,
    csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthenticatedAdmin:
    return service.authenticate(raw_token, csrf, require_csrf=True)


AdminDependency = Annotated[AuthenticatedAdmin, Depends(require_admin)]
AdminCSRFDependency = Annotated[AuthenticatedAdmin, Depends(require_admin_csrf)]


@router.post("/auth/login", response_model=AdminSessionResponse)
def login(
    credentials: AdminLoginRequest,
    request: Request,
    response: Response,
    service: AdminAuthServiceDependency,
    settings: SettingsDependency,
) -> AdminSessionResponse:
    client_key = request.client.host if request.client else "unknown"
    raw_token, session = service.login(
        credentials.username,
        credentials.password,
        client_key,
    )
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=raw_token,
        max_age=settings.admin_session_ttl_minutes * 60,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )
    return session


@router.get("/auth/session", response_model=AdminSessionResponse)
def current_session(admin: AdminDependency) -> AdminSessionResponse:
    return admin.response


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    service: AdminAuthServiceDependency,
    settings: SettingsDependency,
    raw_token: Annotated[str | None, Cookie(alias=ADMIN_COOKIE_NAME)] = None,
    csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Response:
    service.logout(raw_token, csrf)
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/dashboard", response_model=AdminDashboardResponse)
def dashboard(
    service: AdminServiceDependency,
    _admin: AdminDependency,
) -> AdminDashboardResponse:
    return service.dashboard()


@router.get("/issues", response_model=AdminIssueListResponse)
def list_issues(
    service: AdminServiceDependency,
    _admin: AdminDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=255)] = None,
    category: IssueCategory | None = None,
    severity: IssueSeverity | None = None,
    issue_status: Annotated[IssueStatus | None, Query(alias="status")] = None,
) -> AdminIssueListResponse:
    return service.list_issues(
        AdminIssueListQuery(
            page=page,
            page_size=page_size,
            search=search or None,
            category=category,
            severity=severity,
            status=issue_status,
        ),
    )


@router.post("/issues/duplicates", response_model=DuplicateIssueResolutionResponse)
def mark_duplicate_issues(
    request: DuplicateIssueResolutionRequest,
    service: AdminServiceDependency,
    _admin: AdminCSRFDependency,
) -> DuplicateIssueResolutionResponse:
    return service.mark_duplicates(request)


@router.get("/issues/{issue_id}", response_model=AdminIssueDetail)
def get_issue(
    issue_id: UUID,
    service: AdminServiceDependency,
    _admin: AdminDependency,
) -> AdminIssueDetail:
    return service.get_issue(issue_id)


@router.post("/issues/{issue_id}/status", response_model=AdminIssueDetail)
def update_issue_status(
    issue_id: UUID,
    update: AdminStatusUpdateRequest,
    service: AdminServiceDependency,
    _admin: AdminCSRFDependency,
) -> AdminIssueDetail:
    return service.update_status(issue_id, update)


@router.post("/operations/analyze", response_model=OperationsReportResponse)
def analyze_operations(
    service: OperationsServiceDependency,
    _admin: AdminCSRFDependency,
) -> OperationsReportResponse:
    return service.analyze_active_issues()


@router.post("/missions/generate", response_model=MissionGenerationResponse)
def generate_mission_drafts(
    service: MissionGenerationServiceDependency,
    _admin: AdminCSRFDependency,
) -> MissionGenerationResponse:
    return service.generate_drafts()


@router.get("/missions", response_model=AdminMissionListResponse)
def list_admin_missions(
    service: MissionServiceDependency,
    _admin: AdminDependency,
) -> AdminMissionListResponse:
    return service.list_admin()


@router.post("/missions/manual/refine", response_model=ManualMissionDraft)
def refine_manual_mission(
    draft: ManualMissionDraft,
    service: MissionRefinementServiceDependency,
    _admin: AdminCSRFDependency,
) -> ManualMissionDraft:
    return service.refine(draft)


@router.post("/missions/manual", response_model=MissionDetail)
def create_manual_mission(
    mission: ManualMissionCreate,
    service: MissionServiceDependency,
    _admin: AdminCSRFDependency,
) -> MissionDetail:
    return service.create_manual(mission)


@router.post("/missions/{mission_id}/publish", response_model=MissionDetail)
def publish_mission(
    mission_id: UUID,
    service: MissionServiceDependency,
    _admin: AdminCSRFDependency,
) -> MissionDetail:
    return service.publish(mission_id)


@router.delete("/missions/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(
    mission_id: UUID,
    service: MissionServiceDependency,
    _admin: AdminCSRFDependency,
) -> Response:
    service.delete(mission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/missions/{mission_id}/expire", response_model=MissionDetail)
def expire_mission(
    mission_id: UUID,
    service: MissionServiceDependency,
    _admin: AdminCSRFDependency,
) -> MissionDetail:
    return service.expire(mission_id)


@router.post("/missions/{mission_id}/complete", response_model=MissionDetail)
def complete_mission(
    mission_id: UUID,
    service: MissionServiceDependency,
    _admin: AdminCSRFDependency,
) -> MissionDetail:
    return service.complete(mission_id)


@router.get("/operations/latest", response_model=OperationsReportResponse | None)
def latest_operations_report(
    service: OperationsServiceDependency,
    _admin: AdminDependency,
) -> OperationsReportResponse | None:
    return service.latest_report()
