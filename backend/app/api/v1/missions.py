from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import MissionServiceDependency
from app.schemas.missions import MissionDetail, MissionListResponse

router = APIRouter(prefix="/missions", tags=["missions"])


@router.get("", response_model=MissionListResponse)
def list_missions(service: MissionServiceDependency) -> MissionListResponse:
    return service.list_public()


@router.get("/{mission_id}", response_model=MissionDetail)
def get_mission(mission_id: UUID, service: MissionServiceDependency) -> MissionDetail:
    return service.get_public_detail(mission_id)
