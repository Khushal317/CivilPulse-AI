from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("", include_in_schema=False)
def api_root() -> dict[str, str]:
    return {"name": "CivicPulse API", "version": "v1"}

