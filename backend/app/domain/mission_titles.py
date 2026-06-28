import re
import unicodedata
from uuid import UUID

from app.domain.enums import IssueCategory

MISSION_TITLE_PREFIXES = {
    "check",
    "confirm",
    "document",
    "inspect",
    "map",
    "monitor",
    "observe",
    "record",
    "report",
    "review",
    "survey",
    "track",
    "verify",
}


def canonical_mission_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized).strip().lower()
    words = normalized.split()
    while words and words[0] in MISSION_TITLE_PREFIXES:
        words.pop(0)
    return " ".join(words)


def mission_duplicate_key(
    *,
    title: str,
    area_id: UUID,
    category: IssueCategory | None,
) -> tuple[str, UUID, str | None]:
    return (canonical_mission_title(title), area_id, category.value if category else None)
