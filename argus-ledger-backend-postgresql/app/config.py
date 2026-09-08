"""Centralised configuration.

All tunables come from environment variables (or a local ``.env`` file) so the
same image runs unchanged in local dev, CI and Docker. Nothing else in the code
base should call ``os.getenv`` directly — import :func:`get_settings` instead.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from . import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ARGUS Ledger API"
    version: str = __version__

    # PostgreSQL is authoritative. Local default points at a locally installed
    # server; Docker overrides this with the compose service host ("db").
    database_url: str = Field(
        default="postgresql+psycopg://argus:argus_password@localhost:5432/argus"
    )
    # Separate database for the test suite so pytest never touches real data.
    test_database_url: str = Field(
        default="postgresql+psycopg://argus:argus_password@localhost:5432/argus_test"
    )

    # Origins allowed to call the API from a browser (the frontend dev servers).
    # NoDecode: accept a plain comma-separated string from the environment and
    # split it in the validator below (skip pydantic-settings' JSON decoding).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    )

    # Which implementation ``app.ai_service.get_ai_provider`` returns.
    # Member 3 registers real providers alongside "stub".
    ai_provider: str = "stub"

    # A decision at or below this confidence is force-flagged for human review,
    # regardless of what the caller sent.
    human_review_confidence_threshold: float = 0.7

    # SQL echo — handy when debugging query behaviour locally.
    sql_echo: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept ``CORS_ORIGINS=a,b,c`` (and a JSON list) from the environment."""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("["):
                import json

                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
