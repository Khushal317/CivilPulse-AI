import threading
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from app.core.errors import AppError


def now_utc() -> datetime:
    return datetime.now(UTC)


class InMemoryRateLimiter:
    """Small per-process sliding-window limiter for MVP abuse protection."""

    def __init__(self, *, limit: int, window_minutes: int, code: str, message: str) -> None:
        self._limit = limit
        self._window = timedelta(minutes=window_minutes)
        self._code = code
        self._message = message
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, current_time: datetime | None = None) -> None:
        timestamp = current_time or now_utc()
        with self._lock:
            events = self._events[key]
            threshold = timestamp - self._window
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= self._limit:
                raise AppError(
                    code=self._code,
                    message=self._message,
                    status_code=429,
                )
            events.append(timestamp)

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)
