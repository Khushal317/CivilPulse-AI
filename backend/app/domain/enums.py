from enum import StrEnum


class IssueCategory(StrEnum):
    ROAD_DAMAGE = "road_damage"
    GARBAGE_WASTE = "garbage_waste"
    STREETLIGHT = "streetlight"
    WATER_LEAKAGE = "water_leakage"
    DRAINAGE_SEWAGE = "drainage_sewage"
    PUBLIC_SAFETY = "public_safety"
    OTHER = "other"


class IssueSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyLevel(StrEnum):
    ROUTINE = "routine"
    SOON = "soon"
    URGENT = "urgent"
    IMMEDIATE = "immediate"


class IssueStatus(StrEnum):
    REPORTED = "reported"
    COMMUNITY_VERIFIED = "community_verified"
    ESCALATED = "escalated"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class CommunityActionType(StrEnum):
    SAW_THIS_TOO = "saw_this_too"
    STILL_UNRESOLVED = "still_unresolved"
    FIXED = "fixed"
    INCORRECT = "incorrect"


class UpdateActorType(StrEnum):
    SYSTEM = "system"
    ADMIN = "admin"


class IssueSort(StrEnum):
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_VERIFIED = "most_verified"
    SEVERITY = "severity"
