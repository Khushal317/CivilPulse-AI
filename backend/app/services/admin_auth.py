import hashlib
import hmac
import secrets
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.models.admin_session import AdminSession
from app.repositories.admin import AdminSessionRepository
from app.schemas.admin import AdminSessionResponse
from app.services.passwords import verify_password

ADMIN_COOKIE_NAME = "civicpulse_admin_session"
ADMIN_COOKIE_MAX_AGE = 60 * 60 * 24 * 7


def now_utc() -> datetime:
    return datetime.now(UTC)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


class LoginRateLimiter:
    def __init__(self, limit: int, window_minutes: int) -> None:
        self._limit = limit
        self._window = timedelta(minutes=window_minutes)
        self._attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, current_time: datetime) -> None:
        with self._lock:
            attempts = self._attempts[key]
            threshold = current_time - self._window
            while attempts and attempts[0] <= threshold:
                attempts.popleft()
            if len(attempts) >= self._limit:
                raise AppError(
                    code="admin_login_rate_limited",
                    message="Too many login attempts. Please try again later.",
                    status_code=429,
                )

    def record_failure(self, key: str, current_time: datetime) -> None:
        with self._lock:
            self._attempts[key].append(current_time)

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


@lru_cache
def get_login_rate_limiter() -> LoginRateLimiter:
    settings = get_settings()
    return LoginRateLimiter(
        settings.admin_login_rate_limit,
        settings.admin_login_rate_window_minutes,
    )


@dataclass(frozen=True, slots=True)
class AuthenticatedAdmin:
    session: AdminSession
    response: AdminSessionResponse


@dataclass(slots=True)
class AdminAuthService:
    repository: AdminSessionRepository
    settings: Settings
    rate_limiter: LoginRateLimiter

    def login(
        self,
        username: str,
        password: str,
        client_key: str,
    ) -> tuple[str, AdminSessionResponse]:
        current_time = now_utc()
        self.rate_limiter.check(client_key, current_time)
        valid_username = hmac.compare_digest(username, self.settings.admin_username)
        valid_password = verify_password(password, self.settings.admin_password_hash)
        if not (valid_username and valid_password):
            self.rate_limiter.record_failure(client_key, current_time)
            raise AppError(
                code="invalid_admin_credentials",
                message="The administrator username or password is incorrect.",
                status_code=401,
            )

        self.rate_limiter.clear(client_key)
        raw_token = secrets.token_urlsafe(48)
        expires_at = current_time + timedelta(minutes=self.settings.admin_session_ttl_minutes)
        session = self.repository.add(
            AdminSession(
                token_hash=token_hash(raw_token),
                expires_at=expires_at,
                last_seen_at=current_time,
            ),
        )
        return raw_token, self._response(raw_token, session)

    def authenticate(
        self,
        raw_token: str | None,
        supplied_csrf: str | None = None,
        *,
        require_csrf: bool = False,
    ) -> AuthenticatedAdmin:
        if not raw_token:
            raise self._unauthorized()
        session = self.repository.get_by_token_hash(token_hash(raw_token))
        current_time = now_utc()
        if session is None or session.revoked_at is not None or session.expires_at <= current_time:
            raise self._unauthorized()
        expected_csrf = csrf_token(raw_token, self.settings.admin_session_secret)
        if require_csrf and (
            supplied_csrf is None or not hmac.compare_digest(supplied_csrf, expected_csrf)
        ):
            raise AppError(
                code="invalid_csrf_token",
                message="The administrator request could not be verified.",
                status_code=403,
            )
        session.last_seen_at = current_time
        self.repository.flush()
        return AuthenticatedAdmin(
            session=session,
            response=AdminSessionResponse(
                username=self.settings.admin_username,
                expires_at=session.expires_at,
                csrf_token=expected_csrf,
            ),
        )

    def logout(self, raw_token: str | None, supplied_csrf: str | None) -> None:
        authenticated = self.authenticate(
            raw_token,
            supplied_csrf,
            require_csrf=True,
        )
        self.repository.revoke(authenticated.session, now_utc())

    def _response(self, raw_token: str, session: AdminSession) -> AdminSessionResponse:
        return AdminSessionResponse(
            username=self.settings.admin_username,
            expires_at=session.expires_at,
            csrf_token=csrf_token(raw_token, self.settings.admin_session_secret),
        )

    @staticmethod
    def _unauthorized() -> AppError:
        return AppError(
            code="admin_authentication_required",
            message="Administrator authentication is required.",
            status_code=401,
        )
