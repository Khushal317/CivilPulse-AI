from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "CivicPulse AI API"
    app_version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    log_level: str = "INFO"
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    database_url: str = Field(
        default="postgresql+psycopg://civicpulse:civicpulse-local@localhost:5432/civicpulse",
        repr=False,
    )
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=10, ge=1, le=60)
    database_echo: bool = False
    ai_provider: Literal["demo", "gemini"] = "demo"
    gemini_api_key: str | None = Field(default=None, repr=False)
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: int = Field(default=45, ge=5, le=120)
    gemini_max_attempts: int = Field(default=2, ge=1, le=3)
    ai_prompt_version: str = "civic-report-v1"
    report_draft_ttl_minutes: int = Field(default=60, ge=10, le=1_440)
    max_image_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1_048_576)
    max_image_pixels: int = Field(default=40_000_000, ge=1_000_000)
    storage_backend: Literal["local", "gcs"] = "local"
    local_storage_path: Path = Path("storage")
    storage_bucket: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        return value

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver")
        return value

    def model_post_init(self, _context: object) -> None:
        if self.app_env == "production" and self.ai_provider == "demo":
            raise ValueError("AI_PROVIDER=demo is not allowed in production")
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when AI_PROVIDER=gemini")
        if self.storage_backend == "gcs" and not self.storage_bucket:
            raise ValueError("STORAGE_BUCKET is required when STORAGE_BACKEND=gcs")


@lru_cache
def get_settings() -> Settings:
    return Settings()
