import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.request_context import get_request_id

SENSITIVE_KEY_FRAGMENTS = (
    "authorization",
    "cookie",
    "contact",
    "csrf",
    "key",
    "password",
    "secret",
    "session",
    "token",
)


def add_request_id(
    _logger: object,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    request_id = get_request_id()
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "[redacted]"
                if any(fragment in str(key).lower() for fragment in SENSITIVE_KEY_FRAGMENTS)
                else _redact_value(nested)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def redact_sensitive_fields(
    _logger: object,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    for key, value in list(event_dict.items()):
        if any(fragment in str(key).lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
            event_dict[key] = "[redacted]"
        else:
            event_dict[key] = _redact_value(value)
    return event_dict


def configure_logging(log_level: str) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_request_id,
            redact_sensitive_fields,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
