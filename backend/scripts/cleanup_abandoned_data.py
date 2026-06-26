import argparse
import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import create_database_engine
from app.repositories.reports import SQLAlchemyReportRepository
from app.services.cleanup import ReportCleanupService
from app.services.storage import get_image_storage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove expired unpublished report drafts and unreferenced issue images.",
    )
    parser.add_argument("--draft-limit", type=int, default=100)
    parser.add_argument("--image-limit", type=int, default=500)
    parser.add_argument("--skip-unused-images", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    engine = create_database_engine(settings)
    storage = get_image_storage()
    try:
        with Session(engine) as session:
            service = ReportCleanupService(
                repository=SQLAlchemyReportRepository(session),
                storage=storage,
            )
            abandoned = service.cleanup_abandoned_drafts(limit=args.draft_limit)
            unused = (
                service.cleanup_unused_images(limit=args.image_limit)
                if not args.skip_unused_images
                else None
            )
            session.commit()
        payload = {
            "abandoned_drafts": abandoned.abandoned_drafts,
            "abandoned_images": abandoned.abandoned_images,
            "unused_images": unused.unused_images if unused is not None else 0,
        }
        print(json.dumps(payload, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
