from __future__ import annotations

from types import SimpleNamespace

from ares.api.presenters import (
    build_metric_table,
    build_run_decision_payload,
    build_slice_comparison,
    extract_metrics,
    extract_slice_regressions,
)
from ares.gate.decision import build_decision_narrative


def test_extract_metrics_supports_none_mapping_and_object_inputs() -> None:
    assert extract_metrics(None) == {}

    mapping_result = extract_metrics(
        {
            "overall_f1": 0.91,
            "overall_accuracy": 0.92,
            "overall_precision": None,
            "latency_p99_ms": 10.5,
        }
    )
    assert mapping_result == {
        "overall_f1": 0.91,
        "overall_accuracy": 0.92,
        "latency_p99_ms": 10.5,
    }

    obj = SimpleNamespace(overall_f1=0.88, overall_accuracy=0.9, overall_precision=None, model_size_mb=1.2)
    object_result = extract_metrics(obj)
    assert object_result == {
        "overall_f1": 0.88,
        "overall_accuracy": 0.9,
        "model_size_mb": 1.2,
    }


def test_build_metric_table_covers_metric_status_branches() -> None:
    config = {
        "max_regression_f1": 0.02,
        "max_regression_accuracy": 0.015,
        "max_latency_regression_pct": 0.20,
        "max_size_increase_pct": 0.15,
    }
    candidate = {
        "overall_f1": 0.89,
        "overall_accuracy": 0.88,
        "latency_p99_ms": 12.0,
        "model_size_mb": 1.3,
        "custom_metric": 4.0,
        "latency_p50_ms": 4.5,
    }
    champion = {
        "overall_f1": 0.9,
        "overall_accuracy": 0.9,
        "latency_p99_ms": 10.0,
        "model_size_mb": 1.0,
        "custom_metric": 5.0,
        "latency_p50_ms": 5.0,
    }

    table = build_metric_table(candidate, champion, config)
    assert table["overall_f1"]["status"] == "within_tolerance"
    assert table["overall_accuracy"]["status"] == "regressed"
    assert table["latency_p99_ms"]["status"] == "within_tolerance"
    assert table["model_size_mb"]["status"] == "regressed"
    assert table["custom_metric"]["status"] == "regressed"
    assert table["latency_p50_ms"]["status"] == "improved"


def test_extract_slice_regressions_and_slice_comparison_cover_branches() -> None:
    config = {"critical_slice_min_f1": 0.6}
    candidate_slices = {
        "critical": {"f1": 0.55, "is_critical": True},
        "edge_case": {"overall_f1": 0.72},
        "typical": {"f1": 0.91, "is_critical": False},
        "unknown": {},
    }
    champion_slices = {
        "critical": {"f1": 0.7, "is_critical": True},
        "edge_case": {"f1": 0.70, "is_critical": True},
        "typical": {"f1": 0.91, "is_critical": False},
    }

    regressions = extract_slice_regressions(candidate_slices, config)
    assert regressions == [{"slice": "critical", "candidate_f1": 0.55, "threshold": 0.6}]

    comparison = {row["slice"]: row for row in build_slice_comparison(candidate_slices, champion_slices, config)}
    assert comparison["critical"]["status"] == "regressed"
    assert comparison["edge_case"]["status"] == "improved"
    assert comparison["typical"]["status"] == "within_tolerance"
    assert comparison["unknown"]["status"] == "missing"


def test_build_run_decision_payload_covers_baseline_and_comparison_paths() -> None:
    baseline_payload = build_run_decision_payload(
        candidate_metrics={"overall_f1": 0.95},
        champion_metrics={},
        candidate_slices={"critical": {"f1": 0.95, "is_critical": True}},
        champion_slices=None,
        verdict="PASS",
        failure_reason=None,
        config_snapshot={"critical_slice_min_f1": 0.6},
        slice_regressions=[],
    )
    assert "establishes the baseline" in baseline_payload["decision_narrative"]
    assert baseline_payload["metric_table"]["overall_f1"]["status"] == "baseline"

    compared_payload = build_run_decision_payload(
        candidate_metrics={"overall_f1": 0.84, "overall_accuracy": 0.89},
        champion_metrics={"overall_f1": 0.9, "overall_accuracy": 0.9},
        candidate_slices={"typical": {"f1": 0.84, "is_critical": False}},
        champion_slices={"typical": {"f1": 0.9, "is_critical": False}},
        verdict="FAIL",
        failure_reason="overall_f1 regression exceeds tolerance",
        config_snapshot={"critical_slice_min_f1": 0.6},
        slice_regressions=[],
    )
    assert "FAILED" in compared_payload["decision_narrative"]
    assert compared_payload["slice_comparison"][0]["status"] == "regressed"


def test_decision_narrative_handles_failure_without_focus_metric() -> None:
    narrative = build_decision_narrative(
        verdict="FAIL",
        deltas={},
        slice_regressions=[],
        failure_reason="unknown rule failed",
        config_snapshot={"critical_slice_min_f1": 0.6},
    )
    assert "violated one or more configured gate rules" in narrative
    assert "unknown rule failed" in narrative