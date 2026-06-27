from enum import StrEnum


class MissionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class MissionType(StrEnum):
    VERIFICATION = "verification"
    FIX_CONFIRMATION = "fix_confirmation"
    HOTSPOT = "hotspot"
    CATEGORY = "category"
    VOLUNTEER = "volunteer"


class MissionActionType(StrEnum):
    JOINED = "joined"
    VERIFIED_ISSUE = "verified_issue"
    CONFIRMED_UNRESOLVED = "confirmed_unresolved"
    CONFIRMED_FIXED = "confirmed_fixed"
    VOLUNTEERED = "volunteered"
