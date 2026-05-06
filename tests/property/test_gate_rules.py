from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ares.gate.rules_engine import evaluate
from ares.gate.threshold_optimizer import HistoricalRun, optimize_thresholds


def _champion_metrics(quality: float, latency: float, size: float) -> dict[str, float]:
    return {
        "overall_f1": quality,
        "overall_accuracy": quality,
        "latency_p99_ms": latency,
        "model_size_mb": size,
    }


@given(
    st.floats(min_value=0.70, max_value=0.95, allow_nan=False, allow_infinity=False),
    st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=5.0, max_value=80.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.001, max_value=0.015, allow_nan=False, allow_infinity=False),
)
def test_gate_passes_when_candidate_is_above_all_thresholds(
    champion_quality: float,
    champion_latency: float,
    champion_size: float,
    quality_gain: float,
) -> None:
    champion = _champion_metrics(champion_quality, champion_latency, champion_size)
    candidate = {
        "overall_f1": champion_quality + quality_gain,
        "overall_accuracy": champion_quality + quality_gain,
        "latency_p99_ms": champion_latency * 1.05,
        "model_size_mb": champion_size * 1.05,
    }
    decision = evaluate(
        candidate,
        champion,
        {"critical": {"f1": champion_quality + quality_gain, "is_critical": True}},
        {"critical_slice_min_f1": 0.60},
        n_samples=500,
    )
    assert decision.verdict == "PASS"


@given(
    st.floats(min_value=0.75, max_value=0.95, allow_nan=False, allow_infinity=False),
    st.floats(min_value=0.021, max_value=0.20, allow_nan=False, allow_infinity=False),
)
def test_gate_fails_when_a_critical_metric_falls_below_threshold(
    champion_quality: float,
    bad_drop: float,
) -> None:
    champion = _champion_metrics(champion_quality, latency=20.0, size=12.0)
    candidate = {
        "overall_f1": champion_quality - bad_drop,
        "overall_accuracy": champion_quality,
        "latency_p99_ms": 20.0,
        "model_size_mb": 12.0,
    }
    decision = evaluate(
        candidate,
        champion,
        {"critical": {"f1": champion_quality, "is_critical": True}},
        {"max_regression_f1": 0.02},
        n_samples=200,
    )
    assert decision.verdict == "FAIL"


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=0.72, max_value=0.96, allow_nan=False, allow_infinity=False),
            st.floats(min_value=0.72, max_value=0.96, allow_nan=False, allow_infinity=False),
            st.booleans(),
        ),
        min_size=1,
        max_size=10,
    )
)
def test_threshold_optimizer_pass_rate_stays_bounded(
    run_data: list[tuple[float, float, bool]],
) -> None:
    historical_runs = [
        HistoricalRun(
            candidate_metrics={
                "overall_f1": candidate_quality,
                "overall_accuracy": candidate_quality,
                "latency_p99_ms": 25.0,
                "model_size_mb": 15.0,
            },
            champion_metrics={
                "overall_f1": champion_quality,
                "overall_accuracy": champion_quality,
                "latency_p99_ms": 25.0,
                "model_size_mb": 15.0,
            },
            should_pass=should_pass,
            slice_metrics={"critical": {"f1": min(candidate_quality, 0.99), "is_critical": True}},
        )
        for candidate_quality, champion_quality, should_pass in run_data
    ]
    recommendation = optimize_thresholds(historical_runs)
    assert 0.0 <= recommendation.pass_rate <= 1.0
