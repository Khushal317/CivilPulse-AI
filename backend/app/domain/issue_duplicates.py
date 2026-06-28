from datetime import UTC, datetime, timedelta

from app.domain.enums import IssueStatus
from app.models.issue import Issue

DUPLICATE_PUBLIC_RETENTION = timedelta(days=2)
DUPLICATE_PUBLIC_NOTE = (
    "This report was marked as a duplicate. Follow the linked original issue for updates."
)


def now_utc() -> datetime:
    return datetime.now(UTC)


def duplicate_visible_until(issue: Issue) -> datetime | None:
    if issue.duplicate_marked_at is None:
        return None
    marked_at = issue.duplicate_marked_at
    if marked_at.tzinfo is None:
        marked_at = marked_at.replace(tzinfo=UTC)
    return marked_at + DUPLICATE_PUBLIC_RETENTION


def is_publicly_visible_duplicate(issue: Issue, *, current_time: datetime) -> bool:
    if issue.status is not IssueStatus.DUPLICATE:
        return True
    if issue.duplicate_of is not None and issue.duplicate_of.status is IssueStatus.RESOLVED:
        return False
    visible_until = duplicate_visible_until(issue)
    if visible_until is None:
        return False
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)
    return visible_until > current_time
