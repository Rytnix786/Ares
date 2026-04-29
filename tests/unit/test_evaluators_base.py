"""Unit tests for BaseEvaluator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from ares.evaluators.base import BaseEvaluator, EvaluationResult


class MockEvaluator(BaseEvaluator):
    """Mock evaluator for testing BaseEvaluator."""

    def load_model(self) -> None:
        self._model = {"mock": "model"}

    def predict(self, inputs: list) -> list:
        return ["positive"] * len(inputs)

    def compute_metrics(self, predictions: list, ground_truth: list) -> dict[str, float]:
        return {"overall_f1": 0.9, "overall_accuracy": 0.85}


@pytest.fixture
def sample_dataset():
    """Create a sample dataset for testing."""
    return pd.DataFrame({
        "id": ["1", "2", "3", "4", "5"],
        "input": ["text1", "text2", "text3", "text4", "text5"],
        "expected_label": ["positive", "negative", "positive", "negative", "positive"],
        "slice": ["general", "general", "edge_case", "general", "edge_case"],
    })


class TestBaseEvaluator:
    """Test BaseEvaluator functionality."""

    def test_required_columns(self):
        """Test that required columns are defined."""
        assert BaseEvaluator.required_columns == {"id", "input", "expected_label", "slice"}

    def test_initialization(self):
        """Test evaluator initialization."""
        evaluator = MockEvaluator("model_path", {"config": "value"})
        assert evaluator.model_path == "model_path"
        assert evaluator.config == {"config": "value"}
        assert evaluator._model is None

    def test_load_model_called_on_evaluate(self, sample_dataset):
        """Test that load_model is called during evaluate."""
        evaluator = MockEvaluator("model_path")
        assert evaluator._model is None
        
        evaluator.evaluate(sample_dataset, "test-sha")
        
        assert evaluator._model is not None

    def test_evaluate_missing_columns(self, sample_dataset):
        """Test that missing columns raise DatasetSchemaError."""
        evaluator = MockEvaluator("model_path")
        incomplete_dataset = sample_dataset.drop(columns=["expected_label"])
        
        from ares.exceptions import DatasetSchemaError
        with pytest.raises(DatasetSchemaError):
            evaluator.evaluate(incomplete_dataset, "test-sha")

    def test_evaluate_prediction_count_mismatch(self, sample_dataset):
        """Test that prediction count mismatch raises PredictionError."""
        evaluator = MockEvaluator("model_path")
        # Mock predict to return wrong number of predictions
        evaluator.predict = lambda inputs: ["positive"] * (len(inputs) - 1)
        
        from ares.exceptions import PredictionError
        with pytest.raises(PredictionError):
            evaluator.evaluate(sample_dataset, "test-sha")

    def test_evaluate_returns_evaluation_result(self, sample_dataset):
        """Test that evaluate returns EvaluationResult."""
        evaluator = MockEvaluator("model_path")
        result = evaluator.evaluate(sample_dataset, "test-sha")
        
        assert isinstance(result, EvaluationResult)
        assert result.model_id == "model_path"
        assert result.commit_sha == "test-sha"
        assert result.overall_metrics is not None
        assert result.slice_metrics is not None
        assert result.latency_p50_ms >= 0
        assert result.latency_p99_ms >= 0
        assert isinstance(result.passed, bool)
        assert result.raw_predictions is not None

    def test_evaluate_latency_measurement(self, sample_dataset):
        """Test that latency is measured."""
        evaluator = MockEvaluator("model_path")
        result = evaluator.evaluate(sample_dataset, "test-sha")
        
        assert result.latency_p50_ms >= 0
        assert result.latency_p99_ms >= 0
        assert result.latency_p99_ms >= result.latency_p50_ms  # p99 should be >= p50

    def test_evaluate_with_config(self, sample_dataset):
        """Test that config is used in evaluation."""
        config = {"gate": {"critical_slice_min_f1": 0.70}}
        evaluator = MockEvaluator("model_path", config)
        result = evaluator.evaluate(sample_dataset, "test-sha")
        
        assert result is not None

    def test_compute_metrics_called(self, sample_dataset):
        """Test that compute_metrics is called during evaluate."""
        evaluator = MockEvaluator("model_path")
        evaluator.compute_metrics = MagicMock(return_value={"overall_f1": 0.9})
        
        evaluator.evaluate(sample_dataset, "test-sha")
        
        # compute_metrics is called for overall metrics and for each slice
        assert evaluator.compute_metrics.call_count >= 1

    def test_slice_analysis_integration(self, sample_dataset):
        """Test that slice analysis is performed."""
        evaluator = MockEvaluator("model_path")
        result = evaluator.evaluate(sample_dataset, "test-sha")
        
        assert result.slice_metrics is not None
        assert len(result.slice_metrics) > 0


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_evaluation_result_creation(self):
        """Test that EvaluationResult can be created."""
        result = EvaluationResult(
            model_id="model1",
            commit_sha="abc123",
            overall_metrics={"f1": 0.9},
            slice_metrics={"general": {"f1": 0.85}},
            latency_p50_ms=10.0,
            latency_p99_ms=20.0,
            passed=True,
            failure_reason=None,
            raw_predictions=["positive", "negative"],
        )
        
        assert result.model_id == "model1"
        assert result.commit_sha == "abc123"
        assert result.overall_metrics == {"f1": 0.9}
        assert result.slice_metrics == {"general": {"f1": 0.85}}
        assert result.latency_p50_ms == 10.0
        assert result.latency_p99_ms == 20.0
        assert result.passed is True
        assert result.failure_reason is None
        assert result.raw_predictions == ["positive", "negative"]

    def test_evaluation_result_immutable(self):
        """Test that EvaluationResult is frozen (immutable)."""
        result = EvaluationResult(
            model_id="model1",
            commit_sha="abc123",
            overall_metrics={"f1": 0.9},
            slice_metrics={},
            latency_p50_ms=10.0,
            latency_p99_ms=20.0,
            passed=True,
            failure_reason=None,
            raw_predictions=[],
        )
        
        with pytest.raises(AttributeError):
            result.model_id = "model2"
