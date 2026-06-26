from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin_session import AdminSession


class AdminSessionRepository(Protocol):
    def add(self, session: AdminSession) -> AdminSession: ...

    def get_by_token_hash(self, token_hash: str) -> AdminSession | None: ...

    def revoke(self, session: AdminSession, revoked_at: datetime) -> None: ...

    def flush(self) -> None: ...


class SQLAlchemyAdminSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, session: AdminSession) -> AdminSession:
        self._session.add(session)
        self._session.flush()
        return session

    def get_by_token_hash(self, token_hash: str) -> AdminSession | None:
        return self._session.scalar(
            select(AdminSession).where(AdminSession.token_hash == token_hash),
        )

    def revoke(self, session: AdminSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at
        self._session.flush()

    def flush(self) -> None:
        self._session.flush()
