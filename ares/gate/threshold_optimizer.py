from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

from ares.gate.rules_engine import evaluate


@dataclass(frozen=True)
class HistoricalRun:
    candidate_metrics: dict[str, float]
    champion_metrics: dict[str, float]
    should_pass: bool | None = None
    slice_metrics: dict[str, Any] | None = None


@dataclass(frozen=True)
class ThresholdRecommendation:
    config: dict[str, float]
    pass_rate: float
    expected_accuracy: float
    false_pass_rate: float
    false_fail_rate: float
    evaluated_configs: int


def _score(runs: list[HistoricalRun], config: dict[str, float]) -> tuple[float, float, float, float]:
    if not runs:
        return 0.0, 0.0, 0.0, 0.0
    passes = false_pass = false_fail = correct = 0
    labelled = 0
    for run in runs:
        decision = evaluate(run.candidate_metrics, run.champion_metrics, run.slice_metrics, config)
        did_pass = decision.verdict == "PASS"
        passes += int(did_pass)
        if run.should_pass is not None:
            labelled += 1
            correct += int(did_pass == run.should_pass)
            false_pass += int(did_pass and not run.should_pass)
            false_fail += int((not did_pass) and run.should_pass)
    denom = max(labelled, 1)
    return passes / len(runs), correct / denom, false_pass / denom, false_fail / denom


def optimize_thresholds(
    historical_runs: list[HistoricalRun],
    f1_tolerances: list[float] | None = None,
    accuracy_tolerances: list[float] | None = None,
    critical_slice_floors: list[float] | None = None,
) -> ThresholdRecommendation:
    f1_values = f1_tolerances or [0.005, 0.01, 0.02, 0.03]
    acc_values = accuracy_tolerances or [0.005, 0.01, 0.015, 0.02]
    slice_values = critical_slice_floors or [0.55, 0.60, 0.65]
    best: ThresholdRecommendation | None = None
    evaluated = 0
    for f1, acc, floor in product(f1_values, acc_values, slice_values):
        evaluated += 1
        config = {
            "max_regression_f1": float(f1),
            "max_regression_accuracy": float(acc),
            "critical_slice_min_f1": float(floor),
        }
        pass_rate, expected_accuracy, false_pass_rate, false_fail_rate = _score(historical_runs, config)
        recommendation = ThresholdRecommendation(config, pass_rate, expected_accuracy, false_pass_rate, false_fail_rate, evaluated)
        key = (expected_accuracy, -false_pass_rate, -false_fail_rate, pass_rate)
        best_key = (-1.0, -1.0, -1.0, -1.0) if best is None else (best.expected_accuracy, -best.false_pass_rate, -best.false_fail_rate, best.pass_rate)
        if key > best_key:
            best = recommendation
    assert best is not None
    return ThresholdRecommendation(best.config, best.pass_rate, best.expected_accuracy, best.false_pass_rate, best.false_fail_rate, evaluated)
