from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette import status

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.migrations import CURRENT_DATABASE_REVISION
from app.db.session import get_db_session
from app.schemas.health import HealthResponse
from app.services.storage import ImageStorage, get_image_storage

router = APIRouter(prefix="/health", tags=["health"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseDependency = Annotated[Session, Depends(get_db_session)]
StorageDependency = Annotated[ImageStorage, Depends(get_image_storage)]


@router.get("/live", response_model=HealthResponse)
def live(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(
        status="alive",
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", response_model=HealthResponse)
def ready(
    settings: SettingsDependency,
    session: DatabaseDependency,
    storage: StorageDependency,
) -> HealthResponse:
    try:
        revision = session.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1"),
        ).scalar_one_or_none()
    except SQLAlchemyError as exc:
        raise AppError(
            code="database_unavailable",
            message="The database is unavailable or has not been migrated.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    if revision != CURRENT_DATABASE_REVISION:
        raise AppError(
            code="database_revision_mismatch",
            message="The database migration revision is not current.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    storage.health_check()

    return HealthResponse(
        status="ready",
        service=settings.app_name,
        version=settings.app_version,
    )
