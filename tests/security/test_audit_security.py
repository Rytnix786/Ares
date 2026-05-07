from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from ares.api.auth import require_scope
from ares.api.middleware.audit import AuditMiddleware, log_audit_event
from ares.models.audit_log import AuditLog
from ares.observability.metrics import audit_write_failures_total


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

    async def flush(self) -> None:
        return None

    async def refresh(self, entry: AuditLog) -> None:
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


class FailingSessionContext:
    async def __aenter__(self) -> CaptureSession:
        raise RuntimeError("db unavailable")

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        del exc_type, exc, tb


class FailingSessionFactory:
    def __call__(self) -> FailingSessionContext:
        return FailingSessionContext()


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


def _simple_audit_app(audit_sink: list[AuditLog], *, raise_on_post: bool = False) -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        middleware = AuditMiddleware(CaptureSessionFactory(audit_sink))
        return await middleware(request, call_next)

    @app.post("/api/v1/widgets/42")
    async def create_widget(request: Request) -> dict[str, str]:
        del request
        if raise_on_post:
            raise RuntimeError("widget exploded")
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


@pytest.mark.asyncio
async def test_log_audit_event_hashes_list_payload_and_commits() -> None:
    sink: list[AuditLog] = []
    session = CaptureSession(sink)

    await log_audit_event(
        session,
        request_id="req-1",
        user=None,
        endpoint="/api/v1/widgets/42",
        method="POST",
        payload={"items": [{"token": "secret"}]},
        result="success",
        status_code=201,
    )

    assert len(sink) == 1
    assert sink[0].payload_hash is not None
    assert sink[0].user == "anonymous"


def test_audit_middleware_ignores_malformed_json_and_missing_principal() -> None:
    audit_logs: list[AuditLog] = []

    with TestClient(_simple_audit_app(audit_logs)) as client:
        response = client.post(
            "/api/v1/widgets/42",
            headers={"Content-Type": "application/json"},
            content=b"{not-json",
        )

    assert response.status_code == 200
    assert len(audit_logs) == 1
    persisted = audit_logs[0]
    assert persisted.actor_type == "anonymous"
    assert persisted.resource_type == "widgets"
    assert persisted.resource_id == "42"
    assert "payload" not in persisted.audit_metadata


def test_audit_middleware_logs_failed_mutations_with_error_metadata() -> None:
    audit_logs: list[AuditLog] = []

    with pytest.raises(RuntimeError, match="widget exploded"):
        with TestClient(_simple_audit_app(audit_logs, raise_on_post=True)) as client:
            client.post("/api/v1/widgets/42", json={"name": "bad"})

    assert len(audit_logs) == 1
    persisted = audit_logs[0]
    assert persisted.result == "error"
    assert persisted.status_code is None
    assert persisted.audit_metadata["error"] == "widget exploded"
    assert persisted.action == "42"


@pytest.mark.asyncio
async def test_safe_log_audit_event_increments_failure_metric() -> None:
    middleware = AuditMiddleware(FailingSessionFactory())
    before = audit_write_failures_total._value.get()

    await middleware._safe_log_audit_event(  # noqa: SLF001
        request_id="req-2",
        user="user",
        endpoint="/api/v1/widgets/42",
        method="POST",
        payload={"name": "broken"},
        result="success",
        status_code=200,
        audit_metadata={},
    )

    assert audit_write_failures_total._value.get() == before + 1
