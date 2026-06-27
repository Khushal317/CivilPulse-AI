import re
import unicodedata
from enum import StrEnum

DEFAULT_AREA_CITY = "CivicPulse City"
BASELINE_AREA_SCORE = 70


class AreaScoreKey(StrEnum):
    OVERALL = "overall"
    INFRASTRUCTURE = "infrastructure"
    CLEANLINESS = "cleanliness"
    SAFETY = "safety"
    PARTICIPATION = "participation"
    RESPONSIVENESS = "responsiveness"
    ENVIRONMENT = "environment"


class AreaStatusLabel(StrEnum):
    THRIVING = "thriving"
    IMPROVING = "improving"
    STABLE = "stable"
    NEEDS_ATTENTION = "needs_attention"
    AT_RISK = "at_risk"


def normalize_area_name(value: str) -> str:
    """Normalize user-provided location text into a stable public area name."""
    collapsed = " ".join(value.strip().split())
    return collapsed[:255] if collapsed else "Unknown Area"


def area_slug(name: str, city: str = DEFAULT_AREA_CITY) -> str:
    """Build a URL-safe slug scoped to a city."""
    source = f"{city} {name}"
    ascii_text = (
        unicodedata.normalize("NFKD", source)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:180] or "unknown-area"
