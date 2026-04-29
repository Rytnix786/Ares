from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Any

import structlog

try:  # pragma: no cover - exercised through integration when prometheus is installed
    from prometheus_client import Counter, Gauge, Histogram
except Exception:  # pragma: no cover - minimal environments
    Counter = Gauge = Histogram = None


request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")


def get_current_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


def _metric(factory: Any, name: str, description: str, labels: list[str] | None = None) -> Any:
    if factory is None:
        return _NoopMetric()
    try:
        return factory(name, description, labels or [])
    except ValueError:
        # Tests can reload modules in-process; avoid duplicate Prometheus registration failures.
        return _NoopMetric()


class _NoopMetric:
    def labels(self, *_args: Any, **_kwargs: Any) -> _NoopMetric:
        return self

    def inc(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def observe(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def set(self, *_args: Any, **_kwargs: Any) -> None:
        return None


gate_decisions_total = _metric(
    Counter,
    "ares_gate_decisions_total",
    "Total gate decisions by status.",
    ["decision"],
)
evaluation_runs_total = _metric(
    Counter,
    "ares_evaluation_runs_total",
    "Total evaluation runs by status.",
    ["status"],
)
evaluation_latency_seconds = _metric(
    Histogram,
    "ares_evaluation_latency_seconds",
    "Evaluation runtime latency in seconds.",
    ["model_name"],
)
cache_operations_total = _metric(
    Counter,
    "ares_cache_operations_total",
    "Total cache operations by operation and result.",
    ["operation", "result"],
)
active_requests = _metric(
    Gauge,
    "ares_active_requests",
    "Active in-flight API requests.",
)


class MetricsMiddleware:
    """Middleware that binds request_id to all log lines in the request."""

    async def __call__(self, request: Any, call_next: Any) -> Any:
        request_id = getattr(request.state, "request_id", "unknown")
        token = request_id_var.set(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        active_requests.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            active_requests.inc(-1)
            evaluation_latency_seconds.labels("api_request").observe(time.perf_counter() - start)
            request_id_var.reset(token)
            structlog.contextvars.clear_contextvars()
