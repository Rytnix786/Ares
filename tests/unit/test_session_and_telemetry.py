from __future__ import annotations

import sys
import types

from fastapi import FastAPI

from ares.db import session as db_session
from ares.observability import telemetry


def test_get_engine_and_sessionmaker_for_sqlite(monkeypatch):
    monkeypatch.setattr(
        db_session,
        "settings",
        types.SimpleNamespace(
            is_sqlite=True,
            async_database_url="sqlite+aiosqlite:///./tmp-test.db",
            DB_COMMAND_TIMEOUT=10,
            DB_POOL_SIZE=10,
            DB_MAX_OVERFLOW=20,
            DB_POOL_TIMEOUT=30,
        ),
    )
    monkeypatch.setattr(db_session, "engine", None)
    monkeypatch.setattr(db_session, "AsyncSessionLocal", None)
    engine = db_session.get_engine()
    sessionmaker = db_session.get_sessionmaker()
    assert engine is not None
    assert sessionmaker is not None


def test_setup_telemetry_instruments_when_module_available(monkeypatch):
    calls: list[object] = []

    class FakeInstrumentor:
        @staticmethod
        def instrument_app(app):
            calls.append(app)

    module = types.SimpleNamespace(FastAPIInstrumentor=FakeInstrumentor)
    monkeypatch.setitem(sys.modules, "opentelemetry.instrumentation.fastapi", module)
    monkeypatch.setattr(telemetry, "settings", types.SimpleNamespace(OTEL_EXPORTER_OTLP_ENDPOINT="http://otel"))
    app = FastAPI()
    telemetry.setup_telemetry(app)
    assert calls == [app]