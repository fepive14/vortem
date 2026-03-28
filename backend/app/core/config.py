"""Application settings — validated at startup via pydantic-settings."""

from __future__ import annotations

from typing import Literal

from pydantic import AnyUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Allow extra fields from the environment (e.g., POSTGRES_USER) without
        # raising validation errors; they are consumed by docker-compose only.
        extra="ignore",
    )

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        ...,
        description="Async PostgreSQL DSN. Must use postgresql+asyncpg scheme.",
    )

    # Raw asyncpg URL used by the event worker (no SQLAlchemy dialect prefix).
    WORKER_DATABASE_URL: str | None = Field(
        default=None,
        description=(
            "Plain asyncpg DSN for the event worker. "
            "Defaults to DATABASE_URL with the dialect prefix stripped."
        ),
    )

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(..., description="Redis connection URL.")

    # ─── Security ─────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., min_length=32, description="HMAC signing key for JWTs.")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)

    # ─── Application ──────────────────────────────────────────────────────────
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ─── Integrations ─────────────────────────────────────────────────────────
    VOICEHIRE_WEBHOOK_SECRET: str = "change-me-in-production"

    # ─── Derived helpers ──────────────────────────────────────────────────────

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the postgresql+asyncpg:// scheme. "
                f"Got: {v!r}"
            )
        return v

    @property
    def worker_dsn(self) -> str:
        """Plain asyncpg DSN (no dialect prefix) for the event worker."""
        if self.WORKER_DATABASE_URL:
            return self.WORKER_DATABASE_URL
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()  # type: ignore[call-arg]
