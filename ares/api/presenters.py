from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ares.gate.decision import build_decision_narrative

HIGHER_IS_BETTER = {"overall_f1", "overall_accuracy", "overall_precision", "overall_recall"}
LOWER_IS_BETTER = {"latency_p50_ms", "latency_p99_ms", "model_size_mb"}
DEFAULT_CRITICAL_SLICES = {"critical", "edge_case"}


def extract_metrics(run_like: Any) -> dict[str, float]:
    if run_like is None:
        return {}
    if isinstance(run_like, Mapping):
        source = run_like
        return {
            key: float(source.get(key, 0.0))
            for key in [
                "overall_f1",
                "overall_accuracy",
                "overall_precision",
                "overall_recall",
                "latency_p50_ms",
                "latency_p99_ms",
                "model_size_mb",
            ]
            if source.get(key) is not None
        }
    return {
        key: float(getattr(run_like, key, 0.0))
        for key in [
            "overall_f1",
            "overall_accuracy",
            "overall_precision",
            "overall_recall",
            "latency_p50_ms",
            "latency_p99_ms",
            "model_size_mb",
        ]
        if getattr(run_like, key, None) is not None
    }


def _metric_status(metric_name: str, champion: float, candidate: float, config_snapshot: Mapping[str, Any]) -> str:
    delta = candidate - champion
    if metric_name in HIGHER_IS_BETTER:
        tolerance = {
            "overall_f1": float(config_snapshot.get("max_regression_f1", 0.02)),
            "overall_accuracy": float(config_snapshot.get("max_regression_accuracy", 0.015)),
        }.get(metric_name, 0.0)
        if delta > 0:
            return "improved"
        if abs(delta) <= tolerance:
            return "within_tolerance"
        return "regressed"

    if metric_name == "latency_p99_ms":
        if candidate < champion:
            return "improved"
        if champion > 0 and (candidate - champion) / champion > float(config_snapshot.get("max_latency_regression_pct", 0.20)):
            return "regressed"
        return "within_tolerance"

    if metric_name == "model_size_mb":
        if candidate < champion:
            return "improved"
        if champion > 0 and (candidate - champion) / champion > float(config_snapshot.get("max_size_increase_pct", 0.15)):
            return "regressed"
        return "within_tolerance"

    if metric_name in LOWER_IS_BETTER:
        if delta < 0:
            return "improved"
        if delta == 0:
            return "within_tolerance"
        return "regressed"

    if delta > 0:
        return "improved"
    if delta < 0:
        return "regressed"
    return "within_tolerance"


def build_metric_table(
    candidate_metrics: Mapping[str, float],
    champion_metrics: Mapping[str, float],
    config_snapshot: Mapping[str, Any],
) -> dict[str, dict[str, float | str]]:
    rows: dict[str, dict[str, float | str]] = {}
    baseline = not champion_metrics
    for key in sorted(set(candidate_metrics) | set(champion_metrics)):
        champion_value = float(champion_metrics.get(key, 0.0))
        candidate_value = float(candidate_metrics.get(key, 0.0))
        rows[key] = {
            "champion": champion_value,
            "candidate": candidate_value,
            "delta": candidate_value - champion_value,
            "status": "baseline" if baseline else _metric_status(key, champion_value, candidate_value, config_snapshot),
        }
    return rows


def _slice_f1(slice_payload: Any) -> float | None:
    if isinstance(slice_payload, Mapping):
        value = slice_payload.get("f1", slice_payload.get("overall_f1"))
        return None if value is None else float(value)
    return None


def _is_critical_slice(slice_name: str, slice_payload: Any) -> bool:
    if isinstance(slice_payload, Mapping) and "is_critical" in slice_payload:
        return bool(slice_payload.get("is_critical"))
    return slice_name in DEFAULT_CRITICAL_SLICES


def extract_slice_regressions(
    slice_metrics: Mapping[str, Any] | None,
    config_snapshot: Mapping[str, Any],
) -> list[dict[str, Any]]:
    threshold = float(config_snapshot.get("critical_slice_min_f1", 0.60))
    regressions: list[dict[str, Any]] = []
    for slice_name, payload in (slice_metrics or {}).items():
        candidate_f1 = _slice_f1(payload)
        if candidate_f1 is None:
            continue
        if _is_critical_slice(slice_name, payload) and candidate_f1 < threshold:
            regressions.append(
                {
                    "slice": slice_name,
                    "candidate_f1": candidate_f1,
                    "threshold": threshold,
                }
            )
    return regressions


def build_slice_comparison(
    candidate_slices: Mapping[str, Any] | None,
    champion_slices: Mapping[str, Any] | None,
    config_snapshot: Mapping[str, Any],
) -> list[dict[str, Any]]:
    threshold = float(config_snapshot.get("critical_slice_min_f1", 0.60))
    rows: list[dict[str, Any]] = []
    baseline = not champion_slices
    for slice_name in sorted(set(candidate_slices or {}) | set(champion_slices or {})):
        candidate_payload = (candidate_slices or {}).get(slice_name, {})
        champion_payload = (champion_slices or {}).get(slice_name, {})
        candidate_f1 = _slice_f1(candidate_payload)
        champion_f1 = _slice_f1(champion_payload)
        is_critical = _is_critical_slice(slice_name, candidate_payload or champion_payload)
        delta = None if candidate_f1 is None or champion_f1 is None else candidate_f1 - champion_f1

        if candidate_f1 is None:
            status = "missing"
        elif is_critical and candidate_f1 < threshold:
            status = "regressed"
        elif baseline or delta is None:
            status = "baseline"
        elif delta > 0:
            status = "improved"
        elif delta < 0:
            status = "regressed"
        else:
            status = "within_tolerance"

        rows.append(
            {
                "slice": slice_name,
                "champion_f1": champion_f1,
                "candidate_f1": candidate_f1,
                "delta": delta,
                "status": status,
                "threshold": threshold if is_critical else None,
                "is_critical": is_critical,
            }
        )
    return rows


def build_run_decision_payload(
    candidate_metrics: Mapping[str, float],
    champion_metrics: Mapping[str, float],
    candidate_slices: Mapping[str, Any] | None,
    champion_slices: Mapping[str, Any] | None,
    verdict: str,
    failure_reason: str | None,
    config_snapshot: Mapping[str, Any],
    slice_regressions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    deltas = {
        key: float(candidate_metrics.get(key, 0.0)) - float(champion_metrics.get(key, 0.0))
        for key in set(candidate_metrics) | set(champion_metrics)
    }
    slice_regressions = list(slice_regressions or [])
    metric_table = build_metric_table(candidate_metrics, champion_metrics, config_snapshot)
    slice_comparison = build_slice_comparison(candidate_slices, champion_slices, config_snapshot)
    if not champion_metrics:
        narrative = (
            "Candidate PASSED. No champion exists yet, so this run establishes the baseline."
            if verdict.upper() == "PASS"
            else "Candidate FAILED before a champion baseline was established."
        )
    else:
        narrative = build_decision_narrative(
            verdict=verdict,
            deltas=deltas,
            slice_regressions=slice_regressions,
            failure_reason=failure_reason,
            config_snapshot=dict(config_snapshot),
        )
    return {
        "champion_metrics": dict(champion_metrics),
        "delta_metrics": deltas,
        "metric_table": metric_table,
        "slice_comparison": slice_comparison,
        "decision_narrative": narrative,
    }