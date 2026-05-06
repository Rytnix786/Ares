from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class AresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+asyncpg://ares:ares@localhost:55432/ares"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_COMMAND_TIMEOUT: int = 10

    ARES_API_KEY: str | None = None
    ARES_API_KEYS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    ARES_API_KEY_SCOPES: Annotated[dict[str, list[str]], NoDecode] = Field(default_factory=dict)
    ARES_API_URL: str = "http://localhost:8000/api/v1"
    ARES_DASHBOARD_URL: str = "http://localhost:8501"
    CELERY_ENABLED: bool = False
    REDIS_URL: str = "redis://localhost:6379/0"
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_ENDPOINT_URL: str = ""
    DVC_REMOTE_URL: str = "s3://ares-data"

    RATE_LIMIT_EVALUATE: str = "10/minute"
    RATE_LIMIT_CHAMPION_MUTATION: str = "20/minute"
    RATE_LIMIT_READ: str = "120/minute"

    # Zone A: cache settings (Wave 1 Agent B)
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300
    CACHE_KEY_PREFIX: str = "ares"
    CACHE_CONNECT_TIMEOUT_SECONDS: float = 2.0
    CACHE_SOCKET_TIMEOUT_SECONDS: float = 2.0

    # Zone B: DB-managed API keys (Wave 2 Agent D)
    API_KEY_HASH_SECRET: str = "secret"
    API_KEY_DEFAULT_RATE_LIMIT: str = "120/minute"
    API_KEY_HASH_PREFIX_LENGTH: int = 64
    API_KEY_DEFAULT_TTL_DAYS: int = 90
    API_KEY_MAX_TTL_DAYS: int = 365
    SLICE_TREND_RETENTION_DAYS: int = 365

    GOLDEN_SET_VERSION: str = "v1.0.0"
    GOLDEN_SET_REQUIRE_CHECKSUM: bool = False
    GOLDEN_SET_SKIP_CHECKSUM: bool = False
    SLACK_WEBHOOK_URL: str = ""
    GITHUB_TOKEN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    # Zone D/E: MLflow and webhooks (Wave 3A schema support)
    MLFLOW_EXPERIMENT: str = "ares-evaluations"
    WEBHOOK_MAX_RETRIES: int = 3

    # Zone C: feature flags (Wave 3B Agent G)
    ARES_FEATURE_FLAGS: Annotated[dict[str, bool], NoDecode] = Field(default_factory=dict)

    @field_validator("ARES_FEATURE_FLAGS", mode="before")
    @classmethod
    def parse_feature_flags(cls, value: Any) -> dict[str, bool]:
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            return {str(key): bool(flag) for key, flag in parsed.items()} if isinstance(parsed, dict) else {}
        return {str(key): bool(flag) for key, flag in dict(value).items()}

    @field_validator("ARES_API_KEYS", mode="before")
    @classmethod
    def parse_keys(cls, value: Any) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("[") and raw.endswith("]"):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return list(value)

    @field_validator("ARES_API_KEY_SCOPES", mode="before")
    @classmethod
    def parse_key_scopes(cls, value: Any) -> dict[str, list[str]]:
        if value is None or value == "":
            return {}
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return {
                    str(key): [str(scope).strip() for scope in scopes if str(scope).strip()]
                    for key, scopes in parsed.items()
                    if isinstance(scopes, list)
                }
            return {}
        return dict(value)

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

    def scopes_for_api_key(self, api_key: str) -> frozenset[str]:
        if api_key not in self.ARES_API_KEYS:
            return frozenset()
        scopes = self.ARES_API_KEY_SCOPES.get(api_key)
        if scopes is None:
            return frozenset({"read", "write", "admin"})
        return frozenset(scope for scope in scopes if scope)


def load_ares_config(path: str | Path = "ares.config.yaml") -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


@lru_cache
def get_settings() -> AresSettings:
    return AresSettings()


settings = get_settings()
