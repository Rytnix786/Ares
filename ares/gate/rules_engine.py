from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ares.config import load_ares_config
from ares.gate.decision import GateDecision
from ares.metrics.significance import is_improvement_significant


def snapshot_gate_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    if config is None:
        return dict(load_ares_config().get("gate", {}))
    if "gate" in config and isinstance(config.get("gate"), Mapping):
        return dict(config.get("gate", {}))
    return dict(config)


def evaluate(new_metrics: Mapping[str, float], champion_metrics: Mapping[str, float], slice_metrics: Mapping[str, Any] | None = None, config: dict[str, Any] | None = None, n_samples: int = 1) -> GateDecision:
    gate = snapshot_gate_config(config)
    max_f1_drop = float(gate.get("max_regression_f1", 0.02))
    max_acc_drop = float(gate.get("max_regression_accuracy", 0.015))
    critical_floor = float(gate.get("critical_slice_min_f1", 0.60))
    max_latency_pct = float(gate.get("max_latency_regression_pct", 0.20))
    max_size_pct = float(gate.get("max_size_increase_pct", 0.15))
    alpha = float(gate.get("significance_alpha", 0.05))
    deltas = {key: float(new_metrics.get(key, 0.0)) - float(champion_metrics.get(key, 0.0)) for key in set(new_metrics) | set(champion_metrics)}
    failures: list[str] = []
    if deltas.get("overall_f1", 0.0) < -max_f1_drop:
        failures.append(f"overall_f1 regression {deltas['overall_f1']:.4f} exceeds tolerance")
    if deltas.get("overall_accuracy", 0.0) < -max_acc_drop:
        failures.append(f"overall_accuracy regression {deltas['overall_accuracy']:.4f} exceeds tolerance")
    champ_latency = float(champion_metrics.get("latency_p99_ms", 0.0))
    new_latency = float(new_metrics.get("latency_p99_ms", 0.0))
    if champ_latency > 0 and (new_latency - champ_latency) / champ_latency > max_latency_pct:
        failures.append("latency regression exceeds tolerance")
    champ_size = float(champion_metrics.get("model_size_mb", 0.0))
    new_size = float(new_metrics.get("model_size_mb", 0.0))
    if champ_size > 0 and (new_size - champ_size) / champ_size > max_size_pct and deltas.get("overall_accuracy", 0.0) <= 0:
        failures.append("model size increase exceeds tolerance without accuracy gain")
    slice_regressions: list[dict[str, float | str]] = []
    for name, metrics in (slice_metrics or {}).items():
        f1 = float(metrics.get("f1", metrics.get("overall_f1", 0.0))) if isinstance(metrics, dict) else float(getattr(metrics, "metrics", {}).get("f1", 0.0))
        is_critical = bool(metrics.get("is_critical", name in {"critical", "edge_case"})) if isinstance(metrics, dict) else bool(getattr(metrics, "is_critical", name in {"critical", "edge_case"}))
        if is_critical and f1 < critical_floor:
            slice_regressions.append({"slice": str(name), "candidate_f1": f1, "threshold": critical_floor})
    if slice_regressions:
        failures.append("critical slice threshold failed")
    if failures:
        return GateDecision("FAIL", False, "; ".join(failures), deltas, slice_regressions, False)
    improvement, _ = is_improvement_significant(float(new_metrics.get("overall_f1", 0.0)), float(champion_metrics.get("overall_f1", 0.0)), max(n_samples, 1), alpha)
    return GateDecision("PASS", True, "candidate is within configured regression tolerances", deltas, [], deltas.get("overall_f1", 0.0) > 0 and improvement)