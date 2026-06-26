from dataclasses import dataclass
from datetime import UTC, datetime

from app.repositories.reports import ReportRepository
from app.services.storage import ImageStorage


def now_utc() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CleanupResult:
    abandoned_drafts: int = 0
    abandoned_images: int = 0
    unused_images: int = 0


@dataclass(slots=True)
class ReportCleanupService:
    repository: ReportRepository
    storage: ImageStorage

    def cleanup_abandoned_drafts(
        self,
        *,
        cutoff: datetime | None = None,
        limit: int = 100,
    ) -> CleanupResult:
        expired = self.repository.expired_unpublished_drafts(cutoff or now_utc(), limit=limit)
        removed_images = 0
        for draft in expired:
            self.storage.delete(draft.image_key)
            removed_images += 1
            self.repository.delete_draft(draft)
        self.repository.flush()
        return CleanupResult(
            abandoned_drafts=len(expired),
            abandoned_images=removed_images,
        )

    def cleanup_unused_images(
        self,
        *,
        prefix: str = "issues/",
        limit: int = 500,
    ) -> CleanupResult:
        stored_keys = set(self.storage.list_keys(prefix=prefix, limit=limit))
        referenced_keys = self.repository.existing_image_keys(stored_keys)
        unused_keys = sorted(stored_keys - referenced_keys)
        for key in unused_keys:
            self.storage.delete(key)
        return CleanupResult(unused_images=len(unused_keys))
