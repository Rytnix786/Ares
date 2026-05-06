from __future__ import annotations

import hmac
from dataclasses import dataclass

import pytest
from fastapi import Depends, FastAPI, Header, Request
from fastapi.testclient import TestClient

from ares.api.auth import rate_limit_key, require_api_key, require_scope
from ares.api.main import RateLimitExceeded, rate_limit_handler
from ares.config import AresSettings

try:
    from slowapi import Limiter
    from slowapi.middleware import SlowAPIMiddleware
except ModuleNotFoundError:  # pragma: no cover
    Limiter = None
    SlowAPIMiddleware = None


@dataclass(frozen=True)
class FakeDbKey:
    id: str
    scopes: list[str]


class FakeSessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        del exc_type, exc, tb


class FakeSessionFactory:
    def begin(self) -> FakeSessionContext:
        return FakeSessionContext()


def _auth_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected/read")
    async def protected_read(
        request: Request,
        _principal: object = Depends(require_scope("read")),
    ) -> dict[str, bool]:
        del request, _principal
        return {"ok": True}

    @app.post("/protected/write")
    async def protected_write(
        request: Request,
        _principal: object = Depends(require_scope("write")),
    ) -> dict[str, bool]:
        del request, _principal
        return {"ok": True}

    return app


def _patch_auth_db(monkeypatch: pytest.MonkeyPatch, db_key: FakeDbKey | None) -> None:
    async def fake_get_active_api_key_by_hash(_session: object, _key_hash: str) -> FakeDbKey | None:
        return db_key

    async def fake_record_api_key_usage(_session: object, _key_id: str) -> None:
        return None

    async def fake_dispose_engine() -> None:
        return None

    monkeypatch.setattr("ares.api.auth.get_sessionmaker", FakeSessionFactory)
    monkeypatch.setattr("ares.api.auth.get_active_api_key_by_hash", fake_get_active_api_key_by_hash)
    monkeypatch.setattr("ares.api.auth.record_api_key_usage", fake_record_api_key_usage)
    monkeypatch.setattr("ares.api.auth.dispose_engine", fake_dispose_engine)


def test_expired_key_is_rejected_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_db(monkeypatch, None)
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["valid-env-key"]),
    )
    with TestClient(_auth_app()) as client:
        response = client.get("/protected/read", headers={"X-API-Key": "expired-key"})
    assert response.status_code == 401


def test_revoked_key_is_rejected_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_db(monkeypatch, None)
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["valid-env-key"]),
    )
    with TestClient(_auth_app()) as client:
        response = client.get("/protected/read", headers={"X-API-Key": "revoked-key"})
    assert response.status_code == 401


def test_key_without_required_scope_is_rejected_with_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_auth_db(monkeypatch, FakeDbKey(id="db-key-1", scopes=["read"]))
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["fallback-env-key"]),
    )
    with TestClient(_auth_app()) as client:
        response = client.post("/protected/write", headers={"X-API-Key": "db-key"})
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "INSUFFICIENT_SCOPE"


def test_correct_scope_passes_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_auth_db(monkeypatch, FakeDbKey(id="db-key-2", scopes=["read"]))
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["fallback-env-key"]),
    )
    with TestClient(_auth_app()) as client:
        response = client.get("/protected/read", headers={"X-API-Key": "db-key"})
    assert response.status_code == 200


def test_env_key_comparison_uses_constant_time(monkeypatch: pytest.MonkeyPatch) -> None:
    compare_calls: list[tuple[str, str]] = []
    real_compare_digest = hmac.compare_digest

    def tracking_compare_digest(left: str, right: str) -> bool:
        compare_calls.append((left, right))
        return real_compare_digest(left, right)

    _patch_auth_db(monkeypatch, None)
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["env-only-key"]),
    )
    monkeypatch.setattr("ares.api.auth.hmac.compare_digest", tracking_compare_digest)
    with TestClient(_auth_app()) as client:
        response = client.get("/protected/read", headers={"X-API-Key": "env-only-key"})
    assert response.status_code == 200
    assert compare_calls


def test_invalid_key_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    if Limiter is None or SlowAPIMiddleware is None:
        pytest.skip("slowapi is not installed")

    _patch_auth_db(monkeypatch, None)
    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(ENVIRONMENT="production", ARES_API_KEYS=["known-good-key"]),
    )

    limiter = Limiter(key_func=rate_limit_key)
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/limited")
    @limiter.limit("100/minute")
    async def limited(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> dict[str, bool]:
        await require_api_key(x_api_key=x_api_key, request=request)
        return {"ok": True}

    with TestClient(app) as client:
        statuses = [
            client.get("/limited", headers={"X-API-Key": "invalid-key"}).status_code
            for _ in range(101)
        ]
    assert statuses[-1] == 429
