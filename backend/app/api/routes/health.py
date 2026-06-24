from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/live", response_model=HealthResponse)
def live(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(
        status="alive",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", response_model=HealthResponse)
def ready(settings: SettingsDependency) -> HealthResponse:
    # Database and storage readiness checks are added with those integrations.
    return HealthResponse(
        status="ready",
        service=settings.app_name,
        version=settings.app_version,
    )
