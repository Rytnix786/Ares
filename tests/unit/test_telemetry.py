from __future__ import annotations

from types import SimpleNamespace

import pytest

from ares.observability.telemetry import trace_function


class _FakeSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}

    def __enter__(self) -> _FakeSpan:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        del exc_type, exc, tb

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class _FakeTracer:
    def __init__(self) -> None:
        self.spans: list[tuple[str, _FakeSpan]] = []

    def start_as_current_span(self, name: str) -> _FakeSpan:
        span = _FakeSpan()
        self.spans.append((name, span))
        return span


def test_trace_function_creates_span_when_endpoint_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer = _FakeTracer()
    monkeypatch.setattr("ares.observability.telemetry.settings", SimpleNamespace(OTEL_EXPORTER_OTLP_ENDPOINT="http://otel"))
    monkeypatch.setattr("opentelemetry.trace.get_tracer", lambda _name: tracer)

    @trace_function("demo.operation", attributes={"demo.attr": "value", "demo.dynamic": lambda _args, kwargs: kwargs["value"]})
    def add_one(*, value: int) -> int:
        return value + 1

    assert add_one(value=41) == 42
    assert tracer.spans[0][0] == "demo.operation"
    assert tracer.spans[0][1].attributes == {"demo.attr": "value", "demo.dynamic": 41}


def test_trace_function_noop_when_endpoint_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.observability.telemetry.settings", SimpleNamespace(OTEL_EXPORTER_OTLP_ENDPOINT=""))

    @trace_function("demo.noop")
    def multiply(value: int) -> int:
        return value * 2

    assert multiply(21) == 42