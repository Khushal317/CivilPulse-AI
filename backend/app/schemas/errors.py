from typing import Any

from app.schemas.common import APIModel


class ErrorBody(APIModel):
    code: str
    message: str
    details: list[dict[str, Any]]
    request_id: str | None


class ErrorResponse(APIModel):
    error: ErrorBody
