from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from ares.api.auth import require_scope
from ares.api.middleware.audit import AuditMiddleware
from ares.models.audit_log import AuditLog


@dataclass(frozen=True)
class FakeDbKey:
    id: str
    scopes: list[str]


class CaptureSession:
    def __init__(self, sink: list[AuditLog]) -> None:
        self._sink = sink

    def add(self, entry: AuditLog) -> None:
        self._sink.append(entry)

    async def commit(self) -> None:
        return None


class CaptureSessionContext:
    def __init__(self, sink: list[AuditLog]) -> None:
        self._sink = sink

    async def __aenter__(self) -> CaptureSession:
        return CaptureSession(self._sink)

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        del exc_type, exc, tb


class CaptureSessionFactory:
    def __init__(self, sink: list[AuditLog]) -> None:
        self._sink = sink

    def __call__(self) -> CaptureSessionContext:
        return CaptureSessionContext(self._sink)


def _patch_auth_db(monkeypatch: pytest.MonkeyPatch, db_key: FakeDbKey | None) -> None:
    class FakeSessionContext:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            del exc_type, exc, tb

    class FakeSessionFactory:
        def begin(self) -> FakeSessionContext:
            return FakeSessionContext()

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


def _audit_app(audit_sink: list[AuditLog]) -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        middleware = AuditMiddleware(CaptureSessionFactory(audit_sink))
        return await middleware(request, call_next)

    @app.post("/resources")
    async def create_resource(
        request: Request,
        _principal: object = Depends(require_scope("write")),
    ) -> dict[str, str]:
        del request, _principal
        return {"status": "created"}

    @app.put("/resources/1")
    async def update_resource(
        request: Request,
        _principal: object = Depends(require_scope("write")),
    ) -> dict[str, str]:
        del request, _principal
        return {"status": "updated"}

    @app.delete("/resources/1")
    async def delete_resource(
        request: Request,
        _principal: object = Depends(require_scope("write")),
    ) -> dict[str, str]:
        del request, _principal
        return {"status": "deleted"}

    @app.get("/api/v1/audit/events")
    async def audit_events(
        request: Request,
        _principal: object = Depends(require_scope("admin")),
    ) -> dict[str, str]:
        del request, _principal
        return {"status": "ok"}

    return app


def test_every_post_put_and_delete_to_a_resource_creates_an_audit_log_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_logs: list[AuditLog] = []
    _patch_auth_db(monkeypatch, FakeDbKey(id="writer-key-id", scopes=["write", "admin", "read"]))

    with TestClient(_audit_app(audit_logs)) as client:
        assert client.post("/resources", headers={"X-API-Key": "writer-key"}, json={"name": "one"}).status_code == 200
        assert client.put("/resources/1", headers={"X-API-Key": "writer-key"}, json={"name": "two"}).status_code == 200
        assert client.delete("/resources/1", headers={"X-API-Key": "writer-key"}).status_code == 200

    assert [entry.method for entry in audit_logs] == ["POST", "PUT", "DELETE"]


def test_audit_log_query_endpoint_rejects_non_admin_scope_with_403(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_logs: list[AuditLog] = []
    _patch_auth_db(monkeypatch, FakeDbKey(id="reader-key-id", scopes=["read"]))

    with TestClient(_audit_app(audit_logs)) as client:
        response = client.get("/api/v1/audit/events", headers={"X-API-Key": "reader-key"})

    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "INSUFFICIENT_SCOPE"


def test_audit_log_entries_do_not_contain_raw_api_key_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_logs: list[AuditLog] = []
    raw_key = "db-audit-key"
    _patch_auth_db(monkeypatch, FakeDbKey(id="db-key-id", scopes=["write", "admin", "read"]))

    with TestClient(_audit_app(audit_logs)) as client:
        response = client.post("/resources", headers={"X-API-Key": raw_key}, json={"name": "security-test"})

    assert response.status_code == 200
    assert audit_logs
    assert all(entry.api_key_id != raw_key for entry in audit_logs)
    assert all(raw_key not in str(entry.audit_metadata) for entry in audit_logs)


def test_audit_log_entries_redact_sensitive_headers_and_body_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit_logs: list[AuditLog] = []
    _patch_auth_db(monkeypatch, FakeDbKey(id="writer-key-id", scopes=["write", "admin", "read"]))

    body = {
        "name": "security-test",
        "password": "super-secret",
        "secret": "top-secret",
        "token": "abc123",
        "api_key": "raw-api-key",
    }

    with TestClient(_audit_app(audit_logs)) as client:
        response = client.post(
            "/resources",
            headers={
                "X-API-Key": "raw-api-key",
                "Authorization": "Bearer raw-token",
            },
            json=body,
        )

    assert response.status_code == 200
    assert audit_logs
    persisted = audit_logs[0].audit_metadata
    assert persisted["headers"]["Authorization"] == "[REDACTED]"
    assert persisted["headers"]["X-API-Key"] == "[REDACTED]"
    assert persisted["payload"]["password"] == "[REDACTED]"
    assert persisted["payload"]["secret"] == "[REDACTED]"
    assert persisted["payload"]["token"] == "[REDACTED]"
    assert persisted["payload"]["api_key"] == "[REDACTED]"
    assert "raw-token" not in str(persisted)
    assert "raw-api-key" not in str(persisted)
