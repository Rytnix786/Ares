"""Unit tests for gate/rules_engine.py."""

from __future__ import annotations

from ares.gate.decision import GateDecision
from ares.gate.rules_engine import evaluate, snapshot_gate_config


class TestSnapshotGateConfig:
    """Test gate config snapshotting."""

    def test_snapshot_with_none(self):
        """Test snapshot with None config."""
        config = snapshot_gate_config(None)
        assert isinstance(config, dict)
        assert "gate" in config or "max_regression_f1" in config

    def test_snapshot_with_dict(self):
        """Test snapshot with dict config."""
        config = snapshot_gate_config({"gate": {"max_regression_f1": 0.02}})
        assert config["max_regression_f1"] == 0.02

    def test_snapshot_with_mapping(self):
        """Test snapshot with Mapping config."""
        config = snapshot_gate_config({"gate": {"max_regression_f1": 0.02}})
        assert isinstance(config, dict)

    def test_snapshot_with_flat_dict(self):
        """Test snapshot with flat dict (no 'gate' key)."""
        config = snapshot_gate_config({"max_regression_f1": 0.02})
        assert config["max_regression_f1"] == 0.02


class TestEvaluate:
    """Test gate evaluation logic."""

    def test_evaluate_pass(self):
        """Test evaluation that passes."""
        new_metrics = {"overall_f1": 0.9, "overall_accuracy": 0.85}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is True
        assert decision.verdict == "PASS"

    def test_evaluate_f1_regression(self):
        """Test evaluation that fails due to F1 regression."""
        new_metrics = {"overall_f1": 0.80, "overall_accuracy": 0.85}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is False
        assert decision.verdict == "FAIL"
        assert "regression" in decision.reason.lower()

    def test_evaluate_accuracy_regression(self):
        """Test evaluation that fails due to accuracy regression."""
        new_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.75}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is False
        assert "regression" in decision.reason.lower()

    def test_evaluate_latency_regression(self):
        """Test evaluation that fails due to latency regression."""
        new_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8, "latency_p99_ms": 50}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8, "latency_p99_ms": 40}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is False
        assert "latency" in decision.reason.lower()

    def test_evaluate_critical_slice_failure(self):
        """Test evaluation that fails due to critical slice."""
        new_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        slice_metrics = {
            "critical": {"f1": 0.55, "is_critical": True},
        }
        
        decision = evaluate(new_metrics, champion_metrics, slice_metrics=slice_metrics)
        assert decision.passed is False
        assert "critical" in decision.reason.lower()

    def test_evaluate_with_custom_config(self):
        """Test evaluation with custom config."""
        new_metrics = {"overall_f1": 0.80, "overall_accuracy": 0.85}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        config = {"gate": {"max_regression_f1": 0.10}}  # More lenient
        
        decision = evaluate(new_metrics, champion_metrics, config=config)
        assert decision.passed is True  # Should pass with lenient config

    def test_evaluate_returns_gate_decision(self):
        """Test that evaluate returns GateDecision."""
        new_metrics = {"overall_f1": 0.9, "overall_accuracy": 0.85}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert isinstance(decision, GateDecision)
        assert decision.deltas is not None
        assert decision.slice_regressions is not None

    def test_evaluate_deltas_calculation(self):
        """Test that deltas are calculated correctly."""
        new_metrics = {"overall_f1": 0.9, "overall_accuracy": 0.85}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert abs(decision.deltas["overall_f1"] - 0.05) < 0.001
        assert abs(decision.deltas["overall_accuracy"] - 0.05) < 0.001

    def test_evaluate_model_size_increase(self):
        """Test evaluation that fails due to model size increase without accuracy gain."""
        new_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8, "model_size_mb": 12}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8, "model_size_mb": 10}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is False
        assert "size" in decision.reason.lower()

    def test_evaluate_model_size_increase_with_accuracy_gain(self):
        """Test that model size increase is allowed with accuracy gain."""
        new_metrics = {"overall_f1": 0.90, "overall_accuracy": 0.85, "model_size_mb": 12}
        champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8, "model_size_mb": 10}
        
        decision = evaluate(new_metrics, champion_metrics)
        assert decision.passed is True  # Should pass due to accuracy gain
