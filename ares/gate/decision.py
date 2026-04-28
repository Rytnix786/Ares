from __future__ import annotations

from dataclasses import dataclass, field


def _format_metric_name(metric_name: str) -> str:
    return {
        "overall_f1": "F1",
        "overall_accuracy": "accuracy",
        "overall_precision": "precision",
        "overall_recall": "recall",
        "latency_p99_ms": "p99 latency",
        "latency_p50_ms": "p50 latency",
        "model_size_mb": "model size",
    }.get(metric_name, metric_name.replace("_", " "))


def build_decision_narrative(
    verdict: str,
    deltas: dict[str, float],
    slice_regressions: list[dict],
    failure_reason: str | None,
    config_snapshot: dict,
) -> str:
    """Build a human-readable narrative explaining the gate decision."""

    critical_floor = float(config_snapshot.get("critical_slice_min_f1", 0.60))
    preferred_metrics = ["overall_f1", "overall_accuracy", "latency_p99_ms", "model_size_mb"]
    focus_metric = next((metric for metric in preferred_metrics if metric in deltas), None)

    if verdict.upper() == "PASS":
        message_parts = ["Candidate PASSED."]
        if focus_metric is not None:
            delta = float(deltas.get(focus_metric, 0.0))
            metric_label = _format_metric_name(focus_metric)
            if delta > 0:
                message_parts.append(f" {metric_label} improved by {delta:.3f} over champion.")
            elif delta < 0:
                message_parts.append(f" {metric_label} decreased by {abs(delta):.3f} but stayed within configured tolerance.")
            else:
                message_parts.append(f" {metric_label} matched the champion and stayed within configured tolerance.")
        else:
            message_parts.append(" The run stayed within configured regression tolerances.")
        if not slice_regressions:
            message_parts.append(" All critical slices remained above threshold.")
        return "".join(message_parts)

    if slice_regressions:
        first_regression = slice_regressions[0]
        slice_name = first_regression.get("slice", "critical")
        candidate_f1 = float(first_regression.get("candidate_f1", 0.0))
        threshold = float(first_regression.get("threshold", critical_floor))
        message = (
            f"Candidate FAILED. Critical slice '{slice_name}' scored {candidate_f1:.3f}, "
            f"below the required floor of {threshold:.3f}."
        )
        if failure_reason and failure_reason not in message:
            message += f" Reason: {failure_reason}."
        return message

    if focus_metric is not None:
        delta = float(deltas.get(focus_metric, 0.0))
        metric_label = _format_metric_name(focus_metric)
        if delta < 0:
            message = f"Candidate FAILED. {metric_label} regressed by {abs(delta):.3f} beyond the configured tolerance."
        else:
            message = f"Candidate FAILED. {metric_label} did not satisfy the configured promotion rules."
    else:
        message = "Candidate FAILED. The run violated one or more configured gate rules."

    if failure_reason and failure_reason not in message:
        message += f" Reason: {failure_reason}."
    return message


@dataclass(frozen=True)
class GateDecision:
    verdict: str
    passed: bool
    reason: str
    deltas: dict[str, float] = field(default_factory=dict)
    slice_regressions: list[dict[str, float | str]] = field(default_factory=list)
    should_promote: bool = False