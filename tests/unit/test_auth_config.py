from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from ares.api.auth import rate_limit_key, require_api_key
from ares.api.limiting import _NoOpLimiter
from ares.config import AresSettings


def test_rate_limit_key_prefers_api_key() -> None:
    request = cast(Request, SimpleNamespace(headers={"x-api-key": "secret"}, client=SimpleNamespace(host="127.0.0.1")))
    assert rate_limit_key(request) == "secret"


def test_rate_limit_key_falls_back_to_host() -> None:
    request = cast(Request, SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1")))
    assert rate_limit_key(request) == "127.0.0.1"


@pytest.mark.asyncio
async def test_require_api_key_accepts_known_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.api.auth.settings", AresSettings(ENVIRONMENT="development", ARES_API_KEYS=["known-key"]))
    assert await require_api_key("known-key") == "known-key"


@pytest.mark.asyncio
async def test_require_api_key_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.api.auth.settings", AresSettings(ENVIRONMENT="development", ARES_API_KEYS=["known-key"]))
    with pytest.raises(HTTPException):
        await require_api_key("wrong")


def test_settings_merge_legacy_api_key() -> None:
    settings = AresSettings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:5432/ares",
        ARES_API_KEY="legacy",
        ARES_API_KEYS=["current"],
    )
    assert settings.ARES_API_KEYS == ["current", "legacy"]
    assert settings.is_sqlite is False


def test_settings_parse_json_api_keys() -> None:
    settings = AresSettings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:5432/ares",
        ARES_API_KEYS=cast(Any, '["current", "backup"]'),
    )
    assert settings.ARES_API_KEYS == ["current", "backup"]


def test_settings_sqlite_property() -> None:
    settings = AresSettings(ENVIRONMENT="development", DATABASE_URL="sqlite+aiosqlite:///./local.db")
    assert settings.is_sqlite is True


def test_noop_limiter_returns_original_function() -> None:
    limiter = _NoOpLimiter()

    def sample() -> str:
        return "ok"

    wrapped = limiter.limit("10/minute")(sample)
    assert wrapped() == "ok"