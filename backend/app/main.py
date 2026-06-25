from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import get_engine
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    if get_engine.cache_info().currsize:
        get_engine().dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    configure_logging(active_settings.log_level)

    application = FastAPI(
        title=active_settings.app_name,
        version=active_settings.app_version,
        docs_url="/docs" if active_settings.app_env != "production" else None,
        redoc_url="/redoc" if active_settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.dependency_overrides[get_settings] = lambda: active_settings

    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_v1_router)

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "name": active_settings.app_name,
            "version": active_settings.app_version,
            "docs": "/docs",
        }

    return application


app = create_app()
