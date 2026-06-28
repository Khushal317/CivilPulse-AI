from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Request, Response, UploadFile, status
from pydantic import ValidationError

from app.api.dependencies import (
    ReportAnalysisRateLimiterDependency,
    ReportServiceDependency,
    SettingsDependency,
    StorageDependency,
)
from app.core.errors import AppError
from app.domain.enums import IssueCategory
from app.schemas.issues import (
    PublishedReportResponse,
    ReportAnalysisInput,
    ReportDraftResponse,
    ReportDraftUpdate,
)
from app.services.images import validate_image

router = APIRouter(prefix="/reports", tags=["reports"])
media_router = APIRouter(prefix="/media", tags=["media"])


@router.post(
    "/analyze",
    response_model=ReportDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_report(
    request: Request,
    service: ReportServiceDependency,
    settings: SettingsDependency,
    rate_limiter: ReportAnalysisRateLimiterDependency,
    image: Annotated[UploadFile, File(description="One JPEG, PNG, or WebP issue photo")],
    original_description: Annotated[str, Form(min_length=10, max_length=4_000)],
    location: Annotated[str, Form(min_length=2, max_length=255)],
    landmark: Annotated[str | None, Form(max_length=255)] = None,
    preferred_category: Annotated[IssueCategory | None, Form()] = None,
    latitude: Annotated[float | None, Form(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Form(ge=-180, le=180)] = None,
    citizen_name: Annotated[str | None, Form(max_length=120)] = None,
    citizen_contact: Annotated[str | None, Form(max_length=255)] = None,
    urgency_note: Annotated[str | None, Form(max_length=1_000)] = None,
) -> ReportDraftResponse:
    client_key = request.client.host if request.client else "unknown"
    rate_limiter.hit(client_key)
    data = await image.read(settings.max_image_size_bytes + 1)
    validated_image = validate_image(data, settings)
    try:
        report = ReportAnalysisInput(
            original_description=original_description,
            location=location,
            landmark=landmark or None,
            latitude=latitude,
            longitude=longitude,
            preferred_category=preferred_category,
            citizen_name=citizen_name or None,
            citizen_contact=citizen_contact or None,
            urgency_note=urgency_note or None,
        )
    except ValidationError as exc:
        raise AppError(
            code="validation_error",
            message="The report contains invalid data.",
            status_code=422,
            details=[
                {
                    "field": ".".join(str(part) for part in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        ) from exc
    return service.analyze(report, validated_image)


@router.get("/{draft_id}", response_model=ReportDraftResponse)
def get_report_draft(
    draft_id: UUID,
    service: ReportServiceDependency,
) -> ReportDraftResponse:
    return service.get_draft(draft_id)


@router.patch("/{draft_id}", response_model=ReportDraftResponse)
def update_report_draft(
    draft_id: UUID,
    changes: ReportDraftUpdate,
    service: ReportServiceDependency,
) -> ReportDraftResponse:
    return service.update_draft(draft_id, changes)


@router.post("/{draft_id}/publish", response_model=PublishedReportResponse)
def publish_report(
    draft_id: UUID,
    service: ReportServiceDependency,
) -> PublishedReportResponse:
    return service.publish(draft_id)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_report(
    draft_id: UUID,
    service: ReportServiceDependency,
) -> Response:
    service.cancel(draft_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@media_router.get("/{key:path}")
def get_report_image(key: str, storage: StorageDependency) -> Response:
    extension = PurePosixPath(key).suffix.lower()
    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(extension)
    if mime_type is None:
        raise AppError(
            code="invalid_image_key",
            message="The image key is invalid.",
            status_code=404,
        )
    return Response(
        content=storage.read(key),
        media_type=mime_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": "inline; filename=civicpulse-issue-image",
            "X-Content-Type-Options": "nosniff",
        },
    )
