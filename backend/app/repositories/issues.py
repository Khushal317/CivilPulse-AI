from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.issue import Issue


class IssueRepository(Protocol):
    def get_by_id(self, issue_id: UUID) -> Issue | None: ...

    def add(self, issue: Issue) -> Issue: ...


class SQLAlchemyIssueRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, issue_id: UUID) -> Issue | None:
        return self._session.get(Issue, issue_id)

    def add(self, issue: Issue) -> Issue:
        self._session.add(issue)
        self._session.flush()
        return issue
