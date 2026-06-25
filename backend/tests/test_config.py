from app.core.config import Settings


def test_comma_separated_cors_origins_are_parsed() -> None:
    settings = Settings.model_validate(
        {"cors_origins": "http://localhost:5173,https://example.com"},
    )

    assert settings.cors_origins == (
        "http://localhost:5173",
        "https://example.com",
    )
