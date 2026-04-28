from ares.gate.decision import build_decision_narrative
from ares.gate.rules_engine import evaluate


def test_critical_slice_failure_overrides_passing_overall():
    decision = evaluate({"overall_f1": 0.95, "overall_accuracy": 0.95}, {"overall_f1": 0.90, "overall_accuracy": 0.90}, {"critical": {"f1": 0.20, "is_critical": True}})
    assert not decision.passed


def test_regression_within_tolerance_passes():
    decision = evaluate({"overall_f1": 0.895, "overall_accuracy": 0.895}, {"overall_f1": 0.90, "overall_accuracy": 0.90}, {})
    assert decision.passed


def test_regression_beyond_tolerance_fails():
    decision = evaluate({"overall_f1": 0.80, "overall_accuracy": 0.80}, {"overall_f1": 0.90, "overall_accuracy": 0.90}, {})
    assert not decision.passed


def test_statistically_insignificant_improvement_does_not_promote():
    decision = evaluate({"overall_f1": 0.901, "overall_accuracy": 0.90}, {"overall_f1": 0.900, "overall_accuracy": 0.90}, {}, n_samples=100)
    assert decision.passed
    assert not decision.should_promote


def test_decision_narrative_for_pass_mentions_tolerance_and_slices():
    narrative = build_decision_narrative(
        verdict="PASS",
        deltas={"overall_f1": 0.012},
        slice_regressions=[],
        failure_reason=None,
        config_snapshot={"critical_slice_min_f1": 0.6},
    )
    assert "PASSED" in narrative
    assert "improved" in narrative
    assert "critical slices" in narrative


def test_decision_narrative_for_failed_slice_mentions_threshold():
    narrative = build_decision_narrative(
        verdict="FAIL",
        deltas={"overall_f1": -0.05},
        slice_regressions=[{"slice": "critical", "candidate_f1": 0.42, "threshold": 0.6}],
        failure_reason="critical slice threshold failed",
        config_snapshot={"critical_slice_min_f1": 0.6},
    )
    assert "FAILED" in narrative
    assert "critical" in narrative
    assert "0.600" in narrative