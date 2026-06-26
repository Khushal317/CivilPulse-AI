from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Query, Response

from app.api.dependencies import IssueServiceDependency, SettingsDependency
from app.domain.enums import IssueCategory, IssueSeverity, IssueSort, IssueStatus
from app.schemas.issues import (
    CommunityActionCreate,
    CommunityActionResponse,
    IssueListQuery,
    IssueListResponse,
    IssuePublicDetail,
)
from app.services.anonymous_actor import (
    ACTOR_COOKIE_MAX_AGE,
    ACTOR_COOKIE_NAME,
    resolve_anonymous_actor,
)

router = APIRouter(prefix="/issues", tags=["issues"])


def set_actor_cookie(
    response: Response,
    token: str,
    settings: SettingsDependency,
) -> None:
    response.set_cookie(
        key=ACTOR_COOKIE_NAME,
        value=token,
        max_age=ACTOR_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )


@router.get("", response_model=IssueListResponse)
def list_public_issues(
    service: IssueServiceDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 12,
    category: IssueCategory | None = None,
    severity: IssueSeverity | None = None,
    status: IssueStatus | None = None,
    location: Annotated[str | None, Query(max_length=255)] = None,
    sort: IssueSort = IssueSort.NEWEST,
) -> IssueListResponse:
    return service.list_public(
        IssueListQuery(
            page=page,
            page_size=page_size,
            category=category,
            severity=severity,
            status=status,
            location=location or None,
            sort=sort,
        ),
    )


@router.get("/{issue_id}", response_model=IssuePublicDetail)
def get_public_issue(
    issue_id: UUID,
    response: Response,
    service: IssueServiceDependency,
    settings: SettingsDependency,
    actor_token: Annotated[str | None, Cookie(alias=ACTOR_COOKIE_NAME)] = None,
) -> IssuePublicDetail:
    actor = resolve_anonymous_actor(actor_token, settings)
    if actor.is_new:
        set_actor_cookie(response, actor.token, settings)
    return service.get_public_detail(issue_id, actor.actor_hash)


@router.post("/{issue_id}/community-actions", response_model=CommunityActionResponse)
def submit_community_action(
    issue_id: UUID,
    action: CommunityActionCreate,
    response: Response,
    service: IssueServiceDependency,
    settings: SettingsDependency,
    actor_token: Annotated[str | None, Cookie(alias=ACTOR_COOKIE_NAME)] = None,
) -> CommunityActionResponse:
    actor = resolve_anonymous_actor(actor_token, settings)
    if actor.is_new:
        set_actor_cookie(response, actor.token, settings)
    return service.submit_community_action(
        issue_id,
        action.action_type,
        actor.actor_hash,
    )
