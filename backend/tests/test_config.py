import pytest

from app.core.config import Settings
from app.core.logging import redact_sensitive_fields


def test_comma_separated_cors_origins_are_parsed() -> None:
    settings = Settings.model_validate(
        {"cors_origins": "http://localhost:5173,https://example.com"},
    )

    assert settings.cors_origins == (
        "http://localhost:5173",
        "https://example.com",
    )


def test_production_requires_strict_cors_origins() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            ai_provider="gemini",
            gemini_api_key="test-key",
            admin_password_hash="scrypt$placeholder",
            admin_session_secret="production-session-secret",
            anonymous_actor_secret="production-actor-secret",
            cors_origins=("http://localhost:5173",),
        )


def test_logging_redacts_sensitive_fields() -> None:
    redacted = redact_sensitive_fields(
        None,
        "info",
        {
            "event": "admin login",
            "password": "secret",
            "nested": {"gemini_api_key": "key", "citizen_contact": "private@example.com"},
        },
    )

    assert redacted["event"] == "admin login"
    assert redacted["password"] == "[redacted]"
    assert redacted["nested"]["gemini_api_key"] == "[redacted]"
    assert redacted["nested"]["citizen_contact"] == "[redacted]"
