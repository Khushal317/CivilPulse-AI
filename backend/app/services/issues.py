from typing import Protocol
from uuid import UUID

from app.models.issue import Issue


class IssueReader(Protocol):
    def get_public_issue(self, issue_id: UUID) -> Issue: ...
