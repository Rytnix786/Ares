from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://ares:ares@localhost:5432/ares"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_COMMAND_TIMEOUT: int = 10

    ARES_API_KEY: str | None = None
    ARES_API_KEYS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    ARES_API_URL: str = "http://localhost:8000/api/v1"
    ARES_DASHBOARD_URL: str = "http://localhost:8501"
    CELERY_ENABLED: bool = False

    RATE_LIMIT_EVALUATE: str = "10/minute"
    RATE_LIMIT_CHAMPION_MUTATION: str = "20/minute"
    RATE_LIMIT_READ: str = "120/minute"

    GOLDEN_SET_VERSION: str = "v1.0.0"
    GOLDEN_SET_REQUIRE_CHECKSUM: bool = False
    GOLDEN_SET_SKIP_CHECKSUM: bool = False
    SLACK_WEBHOOK_URL: str = ""
    GITHUB_TOKEN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    @field_validator("ARES_API_KEYS", mode="before")
    @classmethod
    def parse_keys(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)

    @model_validator(mode="after")
    def merge_legacy_api_key(self) -> AresSettings:
        keys = list(self.ARES_API_KEYS)
        if self.ARES_API_KEY:
            keys.append(self.ARES_API_KEY)
        self.ARES_API_KEYS = list(dict.fromkeys(k for k in keys if k))
        if self.ENVIRONMENT in {"production", "staging"} and not self.ARES_API_KEYS:
            raise ValueError("ARES_API_KEYS is required in protected environments")
        return self

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL

    @property
    def is_sqlite(self) -> bool:
        return self.async_database_url.startswith("sqlite+")


def load_ares_config(path: str | Path = "ares.config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


@lru_cache
def get_settings() -> AresSettings:
    return AresSettings()


settings = get_settings()