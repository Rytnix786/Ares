from __future__ import annotations

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from fastapi import FastAPI

from ares.config import settings

F = TypeVar("F", bound=Callable[..., Any])


def _resolve_attributes(attributes: dict[str, Any] | None, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    if not attributes:
        return resolved
    for key, value in attributes.items():
        if callable(value):
            value = value(args, kwargs)
        if value is not None:
            resolved[key] = value
    return resolved


def setup_telemetry(app: FastAPI) -> None:
    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception:
        return
    FastAPIInstrumentor.instrument_app(app)


def trace_function(name: str | None = None, attributes: dict[str, Any] | None = None) -> Callable[[F], F]:
    """Decorate a function with an OpenTelemetry span when tracing is configured."""

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                    return await func(*args, **kwargs)
                try:
                    from opentelemetry import trace
                except Exception:
                    return await func(*args, **kwargs)
                tracer = trace.get_tracer("ares")
                with tracer.start_as_current_span(name or func.__qualname__) as span:
                    for key, value in _resolve_attributes(attributes, args, kwargs).items():
                        span.set_attribute(key, value)
                    return await func(*args, **kwargs)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
                return func(*args, **kwargs)
            try:
                from opentelemetry import trace
            except Exception:
                return func(*args, **kwargs)
            tracer = trace.get_tracer("ares")
            with tracer.start_as_current_span(name or func.__qualname__) as span:
                for key, value in _resolve_attributes(attributes, args, kwargs).items():
                    span.set_attribute(key, value)
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator