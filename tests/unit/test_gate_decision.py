"""Unit tests for gate/decision.py."""

from __future__ import annotations

from ares.gate.decision import GateDecision, _format_metric_name, build_decision_narrative


class TestFormatMetricName:
    """Test metric name formatting."""

    def test_format_metric_name_known(self):
        """Test formatting of known metric names."""
        assert _format_metric_name("overall_f1") == "F1"
        assert _format_metric_name("overall_accuracy") == "accuracy"
        assert _format_metric_name("latency_p99_ms") == "p99 latency"
        assert _format_metric_name("model_size_mb") == "model size"

    def test_format_metric_name_unknown(self):
        """Test formatting of unknown metric names."""
        assert _format_metric_name("custom_metric") == "custom metric"
        assert _format_metric_name("some_other_metric") == "some other metric"


class TestBuildDecisionNarrative:
    """Test decision narrative building."""

    def test_pass_narrative_basic(self):
        """Test basic pass narrative."""
        narrative = build_decision_narrative(
            verdict="PASS",
            deltas={"overall_f1": 0.05},
            slice_regressions=[],
            failure_reason=None,
            config_snapshot={"critical_slice_min_f1": 0.60},
        )
        assert "PASSED" in narrative
        assert "improved" in narrative.lower()

    def test_pass_narrative_no_delta(self):
        """Test pass narrative with no delta."""
        narrative = build_decision_narrative(
            verdict="PASS",
            deltas={},
            slice_regressions=[],
            failure_reason=None,
            config_snapshot={"critical_slice_min_f1": 0.60},
        )
        assert "PASSED" in narrative
        assert "tolerance" in narrative.lower()

    def test_fail_narrative_slice_regression(self):
        """Test fail narrative due to slice regression."""
        narrative = build_decision_narrative(
            verdict="FAIL",
            deltas={"overall_f1": 0.02},
            slice_regressions=[{"slice": "critical", "candidate_f1": 0.55, "threshold": 0.60}],
            failure_reason="critical slice threshold failed",
            config_snapshot={"critical_slice_min_f1": 0.60},
        )
        assert "FAILED" in narrative
        assert "critical" in narrative.lower()
        assert "0.55" in narrative

    def test_fail_narrative_metric_regression(self):
        """Test fail narrative due to metric regression."""
        narrative = build_decision_narrative(
            verdict="FAIL",
            deltas={"overall_f1": -0.05},
            slice_regressions=[],
            failure_reason="overall_f1 regression exceeds tolerance",
            config_snapshot={"critical_slice_min_f1": 0.60},
        )
        assert "FAILED" in narrative
        assert "regressed" in narrative.lower()

    def test_fail_narrative_no_reason(self):
        """Test fail narrative without specific reason."""
        narrative = build_decision_narrative(
            verdict="FAIL",
            deltas={},
            slice_regressions=[],
            failure_reason=None,
            config_snapshot={"critical_slice_min_f1": 0.60},
        )
        assert "FAILED" in narrative


class TestGateDecision:
    """Test GateDecision dataclass."""

    def test_gate_decision_creation(self):
        """Test GateDecision creation."""
        decision = GateDecision(
            verdict="PASS",
            passed=True,
            reason="All checks passed",
            deltas={"overall_f1": 0.05},
            slice_regressions=[],
            should_promote=True,
        )
        assert decision.verdict == "PASS"
        assert decision.passed is True
        assert decision.reason == "All checks passed"
        assert decision.deltas == {"overall_f1": 0.05}
        assert decision.slice_regressions == []
        assert decision.should_promote is True

    def test_gate_decision_defaults(self):
        """Test GateDecision with default values."""
        decision = GateDecision(
            verdict="FAIL",
            passed=False,
            reason="Failed",
        )
        assert decision.deltas == {}
        assert decision.slice_regressions == []
        assert decision.should_promote is False
