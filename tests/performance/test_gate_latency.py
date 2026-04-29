from __future__ import annotations

import pytest

from ares.gate.rules_engine import evaluate


@pytest.mark.performance
def test_gate_decision_latency(benchmark: pytest.FixtureRequest) -> None:
    result = benchmark(
        evaluate,
        {"overall_f1": 0.91, "overall_accuracy": 0.93, "latency_p99_ms": 11.0},
        {"overall_f1": 0.90, "overall_accuracy": 0.92, "latency_p99_ms": 10.0},
        {"critical": {"f1": 0.91, "is_critical": True}},
        {"critical_slice_min_f1": 0.60},
        25,
    )
    assert result.passed is True
