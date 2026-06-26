from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.errors import AppError
from app.models.admin_session import AdminSession
from app.repositories.admin import AdminSessionRepository
from app.services.admin_auth import AdminAuthService, LoginRateLimiter
from app.services.passwords import hash_password, verify_password


class FakeAdminSessionRepository(AdminSessionRepository):
    def __init__(self) -> None:
        self.sessions: dict[str, AdminSession] = {}

    def add(self, session: AdminSession) -> AdminSession:
        session.id = session.id or uuid4()
        session.created_at = datetime.now(UTC)
        self.sessions[session.token_hash] = session
        return session

    def get_by_token_hash(self, token_hash: str) -> AdminSession | None:
        return self.sessions.get(token_hash)

    def revoke(self, session: AdminSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at

    def flush(self) -> None:
        return None


def build_auth(*, rate_limit: int = 5) -> tuple[AdminAuthService, FakeAdminSessionRepository]:
    repository = FakeAdminSessionRepository()
    service = AdminAuthService(
        repository=repository,
        settings=Settings(
            admin_username="admin",
            admin_password_hash=hash_password("correct-password"),
            admin_session_secret="test-session-secret",
            admin_session_ttl_minutes=60,
        ),
        rate_limiter=LoginRateLimiter(rate_limit, 15),
    )
    return service, repository


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("secret")
    second = hash_password("secret")

    assert first != second
    assert verify_password("secret", first) is True
    assert verify_password("wrong", first) is False


def test_login_session_csrf_logout_and_revocation() -> None:
    service, repository = build_auth()

    raw_token, session = service.login("admin", "correct-password", "127.0.0.1")
    authenticated = service.authenticate(
        raw_token,
        session.csrf_token,
        require_csrf=True,
    )
    service.logout(raw_token, session.csrf_token)

    assert len(repository.sessions) == 1
    stored = next(iter(repository.sessions.values()))
    assert raw_token not in stored.token_hash
    assert authenticated.response.username == "admin"
    assert stored.revoked_at is not None
    with pytest.raises(AppError) as caught:
        service.authenticate(raw_token)
    assert caught.value.code == "admin_authentication_required"


def test_invalid_expired_and_csrf_sessions_are_rejected() -> None:
    service, repository = build_auth()

    with pytest.raises(AppError) as invalid:
        service.login("admin", "wrong", "client")
    assert invalid.value.code == "invalid_admin_credentials"
    assert repository.sessions == {}

    raw_token, session = service.login("admin", "correct-password", "client")
    with pytest.raises(AppError) as csrf:
        service.authenticate(raw_token, "wrong-csrf", require_csrf=True)
    assert csrf.value.code == "invalid_csrf_token"

    stored = next(iter(repository.sessions.values()))
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    with pytest.raises(AppError) as expired:
        service.authenticate(raw_token)
    assert expired.value.code == "admin_authentication_required"
    assert session.username == "admin"


def test_failed_logins_are_rate_limited_and_success_clears_failures() -> None:
    service, _repository = build_auth(rate_limit=2)

    for _attempt in range(2):
        with pytest.raises(AppError):
            service.login("admin", "wrong", "client")
    with pytest.raises(AppError) as limited:
        service.login("admin", "correct-password", "client")
    assert limited.value.code == "admin_login_rate_limited"

    other_service, _ = build_auth(rate_limit=2)
    other_service.login("admin", "correct-password", "other-client")
    with pytest.raises(AppError) as failure:
        other_service.login("admin", "wrong", "other-client")
    assert failure.value.code == "invalid_admin_credentials"
