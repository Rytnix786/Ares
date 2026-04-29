from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from ares.api.auth import APIKeyPrincipal, rate_limit_key, require_api_key, require_scope
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
    principal = await require_api_key("known-key")
    assert principal.key == "known-key"
    assert principal.scopes == frozenset({"read", "write", "admin"})


@pytest.mark.asyncio
async def test_require_api_key_rejects_unknown_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.api.auth.settings", AresSettings(ENVIRONMENT="development", ARES_API_KEYS=["known-key"]))
    with pytest.raises(HTTPException):
        await require_api_key("wrong")


@pytest.mark.asyncio
async def test_require_api_key_allows_development_without_configured_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="development", ARES_API_KEYS=[]),
    )

    principal = await require_api_key(None)

    assert principal.key == "development"
    assert principal.scopes == frozenset({"read", "write", "admin"})


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


def test_api_key_principal_supports_scope_checks() -> None:
    principal = APIKeyPrincipal(key="reader", key_id="reader", scopes=frozenset({"read"}))

    assert principal.has_scope("read") is True
    assert principal.has_scope("write") is False


def test_require_scope_rejects_principal_without_scope() -> None:
    dependency = require_scope("admin")
    principal = APIKeyPrincipal(key="reader", key_id="reader", scopes=frozenset({"read"}))

    with pytest.raises(HTTPException) as exc_info:
        dependency(principal)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "INSUFFICIENT_SCOPE"


def test_settings_parses_api_key_scopes() -> None:
    settings = AresSettings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:5432/ares",
        ARES_API_KEYS=["reader", "admin"],
        ARES_API_KEY_SCOPES=cast(Any, '{"reader": ["read"], "admin": ["read", "write", "admin"]}'),
    )

    assert settings.scopes_for_api_key("reader") == frozenset({"read"})
    assert settings.scopes_for_api_key("admin") == frozenset({"read", "write", "admin"})
    assert settings.scopes_for_api_key("unknown") == frozenset()


def test_settings_defaults_legacy_keys_to_full_scope() -> None:
    settings = AresSettings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:5432/ares",
        ARES_API_KEYS=["legacy"],
    )

    assert settings.scopes_for_api_key("legacy") == frozenset({"read", "write", "admin"})


def test_noop_limiter_returns_original_function() -> None:
    limiter = _NoOpLimiter()

    def sample() -> str:
        return "ok"

    wrapped = limiter.limit("10/minute")(sample)
    assert wrapped() == "ok"