from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette import status

from app.core.request_context import get_request_id


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = status.HTTP_400_BAD_REQUEST
    details: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def error_payload(
    *,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": get_request_id(),
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_payload(
                code="validation_error",
                message="The request contains invalid data.",
                details=details,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_payload(
                code="database_unavailable",
                message="The database is unavailable. Please try again later.",
            ),
        )
