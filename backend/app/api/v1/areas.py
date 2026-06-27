from fastapi import APIRouter

from app.api.dependencies import AreaServiceDependency
from app.schemas.areas import AreaDetail, AreaListResponse

router = APIRouter(prefix="/areas", tags=["areas"])


@router.get("", response_model=AreaListResponse)
def list_areas(service: AreaServiceDependency) -> AreaListResponse:
    return service.list_public()


@router.get("/{slug}", response_model=AreaDetail)
def get_area(slug: str, service: AreaServiceDependency) -> AreaDetail:
    return service.get_public_detail(slug)
