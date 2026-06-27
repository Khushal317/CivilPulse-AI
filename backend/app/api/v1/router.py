from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.areas import router as areas_router
from app.api.v1.issues import router as issues_router
from app.api.v1.missions import router as missions_router
from app.api.v1.reports import media_router
from app.api.v1.reports import router as reports_router
from app.domain.enums import (
    CommunityActionType,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    UrgencyLevel,
)

router = APIRouter(prefix="/api/v1")
router.include_router(admin_router)
router.include_router(areas_router)
router.include_router(issues_router)
router.include_router(missions_router)
router.include_router(reports_router)
router.include_router(media_router)


@router.get("", include_in_schema=False)
def api_root() -> dict[str, str]:
    return {"name": "CivicPulse API", "version": "v1"}


@router.get("/meta", tags=["system"])
def api_metadata() -> dict[str, object]:
    return {
        "api_version": "v1",
        "categories": [value.value for value in IssueCategory],
        "severities": [value.value for value in IssueSeverity],
        "urgency_levels": [value.value for value in UrgencyLevel],
        "statuses": [value.value for value in IssueStatus],
        "community_actions": [value.value for value in CommunityActionType],
    }
