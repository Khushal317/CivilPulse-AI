from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.issue import Issue
from app.models.issue_draft import IssueDraft


class ReportRepository(Protocol):
    def add_draft(self, draft: IssueDraft) -> IssueDraft: ...

    def get_draft(self, draft_id: UUID, *, for_update: bool = False) -> IssueDraft | None: ...

    def delete_draft(self, draft: IssueDraft) -> None: ...

    def add_issue(self, issue: Issue) -> Issue: ...

    def find_issue_by_image_key(self, image_key: str) -> Issue | None: ...

    def expired_unpublished_drafts(self, cutoff: datetime, *, limit: int) -> list[IssueDraft]: ...

    def existing_image_keys(self, image_keys: set[str]) -> set[str]: ...

    def flush(self) -> None: ...


class SQLAlchemyReportRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_draft(self, draft: IssueDraft) -> IssueDraft:
        self._session.add(draft)
        self._session.flush()
        return draft

    def get_draft(self, draft_id: UUID, *, for_update: bool = False) -> IssueDraft | None:
        statement = select(IssueDraft).where(IssueDraft.id == draft_id)
        if for_update:
            statement = statement.with_for_update()
        return self._session.scalar(statement)

    def delete_draft(self, draft: IssueDraft) -> None:
        self._session.delete(draft)

    def add_issue(self, issue: Issue) -> Issue:
        self._session.add(issue)
        self._session.flush()
        return issue

    def find_issue_by_image_key(self, image_key: str) -> Issue | None:
        return self._session.scalar(select(Issue).where(Issue.image_key == image_key))

    def expired_unpublished_drafts(self, cutoff: datetime, *, limit: int) -> list[IssueDraft]:
        return list(
            self._session.scalars(
                select(IssueDraft)
                .where(IssueDraft.published_at.is_(None), IssueDraft.expires_at <= cutoff)
                .order_by(IssueDraft.expires_at, IssueDraft.id)
                .limit(limit)
                .with_for_update(skip_locked=True),
            ).all(),
        )

    def existing_image_keys(self, image_keys: set[str]) -> set[str]:
        if not image_keys:
            return set()
        draft_keys = set(
            self._session.scalars(
                select(IssueDraft.image_key).where(IssueDraft.image_key.in_(image_keys)),
            ).all(),
        )
        issue_keys = set(
            self._session.scalars(
                select(Issue.image_key).where(Issue.image_key.in_(image_keys)),
            ).all(),
        )
        return draft_keys | issue_keys

    def flush(self) -> None:
        self._session.flush()


def utc_now() -> datetime:
    return datetime.now().astimezone()
