from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Response

from app.api.dependencies import MissionServiceDependency, SettingsDependency
from app.api.v1.issues import set_actor_cookie
from app.schemas.missions import (
    MissionActionCreate,
    MissionActionResponse,
    MissionDetail,
    MissionListResponse,
)
from app.services.anonymous_actor import (
    ACTOR_COOKIE_NAME,
    resolve_anonymous_actor,
)

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=MissionListResponse)
def list_missions(service: MissionServiceDependency) -> MissionListResponse:
    return service.list_public()


@router.get("/{mission_id}", response_model=MissionDetail)
def get_mission(
    mission_id: UUID,
    response: Response,
    service: MissionServiceDependency,
    settings: SettingsDependency,
    actor_token: Annotated[str | None, Cookie(alias=ACTOR_COOKIE_NAME)] = None,
) -> MissionDetail:
    actor = resolve_anonymous_actor(actor_token, settings)
    if actor.is_new:
        set_actor_cookie(response, actor.token, settings)
    return service.get_public_detail(mission_id, actor.actor_hash)


@router.post("/{mission_id}/actions", response_model=MissionActionResponse)
def submit_mission_action(
    mission_id: UUID,
    action: MissionActionCreate,
    response: Response,
    service: MissionServiceDependency,
    settings: SettingsDependency,
    actor_token: Annotated[str | None, Cookie(alias=ACTOR_COOKIE_NAME)] = None,
) -> MissionActionResponse:
    actor = resolve_anonymous_actor(actor_token, settings)
    if actor.is_new:
        set_actor_cookie(response, actor.token, settings)
    return service.submit_action(
        mission_id,
        action.action_type,
        actor.actor_hash,
        issue_id=action.issue_id,
    )
