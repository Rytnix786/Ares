from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from fastapi import FastAPI

from ares.config import settings

F = TypeVar("F", bound=Callable[..., Any])


def setup_telemetry(app: FastAPI) -> None:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception:
        return
    FastAPIInstrumentor.instrument_app(app)


def trace_function(name: str | None = None) -> Callable[[F], F]:
    """Decorate a function with an OpenTelemetry span when tracing is configured."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                return func(*args, **kwargs)
            try:
                from opentelemetry import trace
            except Exception:
                return func(*args, **kwargs)
            tracer = trace.get_tracer("ares")
            with tracer.start_as_current_span(name or func.__qualname__):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator