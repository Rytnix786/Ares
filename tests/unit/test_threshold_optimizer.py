from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ares.gate.threshold_optimizer import HistoricalRun, optimize_thresholds


def test_threshold_optimizer_recommends_config_on_seeded_history() -> None:
    runs = [
        HistoricalRun({"overall_f1": 0.91, "overall_accuracy": 0.92}, {"overall_f1": 0.90, "overall_accuracy": 0.91}, True),
        HistoricalRun({"overall_f1": 0.84, "overall_accuracy": 0.85}, {"overall_f1": 0.90, "overall_accuracy": 0.91}, False),
    ]

    recommendation = optimize_thresholds(runs)

    assert recommendation.config["max_regression_f1"] > 0
    assert 0.0 <= recommendation.pass_rate <= 1.0
    assert recommendation.evaluated_configs == 48


@given(st.lists(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False), min_size=1, max_size=10))
def test_threshold_optimizer_rates_stay_bounded(values: list[float]) -> None:
    runs = [
        HistoricalRun(
            {"overall_f1": value, "overall_accuracy": value},
            {"overall_f1": 0.5, "overall_accuracy": 0.5},
            value >= 0.5,
        )
        for value in values
    ]

    recommendation = optimize_thresholds(runs, f1_tolerances=[0.01], accuracy_tolerances=[0.01], critical_slice_floors=[0.6])

    assert 0.0 <= recommendation.pass_rate <= 1.0
    assert 0.0 <= recommendation.expected_accuracy <= 1.0
    assert 0.0 <= recommendation.false_pass_rate <= 1.0
    assert 0.0 <= recommendation.false_fail_rate <= 1.0
