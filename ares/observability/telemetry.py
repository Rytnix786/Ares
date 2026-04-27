from __future__ import annotations

from fastapi import FastAPI

from ares.config import settings


def setup_telemetry(app: FastAPI) -> None:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception:
        return
    FastAPIInstrumentor.instrument_app(app)