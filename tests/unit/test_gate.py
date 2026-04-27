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