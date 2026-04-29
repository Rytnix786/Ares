"""Unit tests for ClassificationEvaluator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import joblib
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from ares.evaluators.classification import ClassificationEvaluator
from ares.exceptions import PredictionError


@pytest.fixture
def sample_dataset():
    """Create a sample dataset for testing."""
    return pd.DataFrame({
        "id": ["1", "2", "3", "4", "5"],
        "input": [
            "This is a positive review",
            "This is a negative issue",
            "Great product, resolved",
            "Failed system, broken",
            "Clear documentation",
        ],
        "expected_label": ["positive", "negative", "positive", "negative", "positive"],
        "slice": ["general", "general", "edge_case", "general", "edge_case"],
    })


class TestClassificationEvaluator:
    """Test ClassificationEvaluator functionality."""

    def test_load_model_joblib(self, tmp_path):
        """Test loading a joblib model."""
        # Create a mock joblib file
        model_path = tmp_path / "model.joblib"
        model_path.touch()  # Create the file
        
        mock_model = {"scaler": None, "model": MagicMock()}
        
        with patch("joblib.load", return_value=mock_model):
            evaluator = ClassificationEvaluator(str(model_path))
            evaluator.load_model()
            assert evaluator._model == mock_model

    def test_load_model_json(self, tmp_path):
        """Test loading a JSON model."""
        model_path = tmp_path / "model.json"
        model_path.write_text('{"default_label": "positive", "positive_keywords": ["great"], "negative_keywords": ["bad"]}')
        
        evaluator = ClassificationEvaluator(str(model_path))
        evaluator.load_model()
        assert evaluator._model is not None
        assert evaluator._model["default_label"] == "positive"

    def test_load_model_no_file(self):
        """Test loading when file doesn't exist (uses default)."""
        evaluator = ClassificationEvaluator("nonexistent.json")
        evaluator.load_model()
        assert evaluator._model is not None
        assert "default_label" in evaluator._model

    def test_predict_with_dict_model(self, sample_dataset):
        """Test prediction with dict-based model."""
        evaluator = ClassificationEvaluator("model.json")
        evaluator._model = {
            "default_label": "positive",
            "positive_keywords": ["positive", "great", "resolved"],
            "negative_keywords": ["negative", "failed", "broken"],
        }
        
        predictions = evaluator.predict(sample_dataset["input"].tolist())
        assert len(predictions) == len(sample_dataset)
        assert all(isinstance(p, str) for p in predictions)

    def test_predict_with_label_in_dict(self, sample_dataset):
        """Test prediction when input has label field."""
        evaluator = ClassificationEvaluator("model.json")
        evaluator._model = {"default_label": "positive"}
        
        # Add label to input
        inputs_with_label = [{"text": "test", "label": "negative"}]
        predictions = evaluator.predict(inputs_with_label)
        assert predictions == ["negative"]

    def test_predict_with_text_field(self, sample_dataset):
        """Test prediction with text field."""
        evaluator = ClassificationEvaluator("model.json")
        evaluator._model = {
            "default_label": "positive",
            "positive_keywords": ["positive"],
            "negative_keywords": ["negative"],
        }
        
        inputs_with_text = [{"text": "This is positive"}]
        predictions = evaluator.predict(inputs_with_text)
        assert predictions == ["positive"]

    def test_predict_default_fallback(self, sample_dataset):
        """Test prediction falls back to default label."""
        evaluator = ClassificationEvaluator("model.json")
        evaluator._model = {"default_label": "neutral"}
        
        predictions = evaluator.predict(["unknown input"])
        assert predictions == ["neutral"]

    def test_compute_metrics(self):
        """Test metric computation."""
        evaluator = ClassificationEvaluator("model.json")
        predictions = ["positive", "negative", "positive", "negative", "positive"]
        ground_truth = ["positive", "negative", "positive", "negative", "negative"]
        
        metrics = evaluator.compute_metrics(predictions, ground_truth)
        assert "overall_f1" in metrics
        assert "overall_accuracy" in metrics
        assert "overall_precision" in metrics
        assert "overall_recall" in metrics
        assert 0 <= metrics["overall_f1"] <= 1
        assert 0 <= metrics["overall_accuracy"] <= 1

    def test_compute_metrics_perfect(self):
        """Test metric computation with perfect predictions."""
        evaluator = ClassificationEvaluator("model.json")
        predictions = ["positive", "negative", "positive", "negative"]
        ground_truth = ["positive", "negative", "positive", "negative"]
        
        metrics = evaluator.compute_metrics(predictions, ground_truth)
        assert metrics["overall_accuracy"] == 1.0
        assert metrics["overall_f1"] == 1.0

    def test_compute_metrics_zero_division(self):
        """Test metric computation handles zero division."""
        evaluator = ClassificationEvaluator("model.json")
        predictions = ["positive", "positive", "positive", "positive"]
        ground_truth = ["negative", "negative", "negative", "negative"]
        
        metrics = evaluator.compute_metrics(predictions, ground_truth)
        # Should handle zero division gracefully
        assert metrics["overall_accuracy"] == 0.0
        assert metrics["overall_f1"] == 0.0

    def test_evaluate_integration(self, sample_dataset):
        """Test full evaluation pipeline."""
        evaluator = ClassificationEvaluator("model.json")
        evaluator._model = {
            "default_label": "positive",
            "positive_keywords": ["positive", "great", "resolved"],
            "negative_keywords": ["negative", "failed", "broken"],
        }
        
        result = evaluator.evaluate(sample_dataset, "test-sha")
        assert result is not None
        assert result.commit_sha == "test-sha"
        assert result.overall_metrics is not None
        assert result.slice_metrics is not None
        assert result.latency_p50_ms >= 0
        assert result.latency_p99_ms >= 0

    def test_evaluate_with_config(self, sample_dataset):
        """Test evaluation with custom config."""
        config = {"gate": {"critical_slice_min_f1": 0.70}}
        evaluator = ClassificationEvaluator("model.json", config)
        evaluator._model = {
            "default_label": "positive",
            "positive_keywords": ["positive"],
            "negative_keywords": ["negative"],
        }
        
        result = evaluator.evaluate(sample_dataset, "test-sha")
        assert result is not None

    def test_model_load_error(self, tmp_path):
        """Test that ModelLoadError is raised on load failure."""
        model_path = tmp_path / "model.joblib"
        model_path.touch()  # Create the file so it tries joblib.load
        
        with patch("joblib.load", side_effect=Exception("Load failed")):
            from ares.exceptions import ModelLoadError
            evaluator = ClassificationEvaluator(str(model_path))
            with pytest.raises(ModelLoadError):
                evaluator.load_model()

    def test_explicit_sklearn_tabular_mode_evaluates_dict_payloads(self, tmp_path):
        """Adult-style tabular payloads route through sklearn predict when explicitly configured."""
        model_path = tmp_path / "adult.joblib"
        model = DummyClassifier(strategy="most_frequent")
        train_x = pd.DataFrame({"age": [24, 55, 44], "hours-per-week": [35, 50, 45]})
        train_y = ["negative", "positive", "positive"]
        model.fit(train_x, train_y)
        joblib.dump(model, model_path)

        dataset = pd.DataFrame(
            {
                "id": ["1", "2"],
                "input": [
                    {"age": 39, "hours-per-week": 40},
                    {"age": 52, "hours-per-week": 55},
                ],
                "expected_label": ["positive", "positive"],
                "slice": ["critical", "typical"],
            }
        )
        config = {
            "evaluator": {
                "mode": "sklearn_tabular",
                "feature_columns": ["age", "hours-per-week"],
                "positive_label": "positive",
                "negative_label": "negative",
            },
            "gate": {"critical_slice_min_f1": 0.5},
        }

        result = ClassificationEvaluator(str(model_path), config).evaluate(dataset, "adult-test")

        assert result.commit_sha == "adult-test"
        assert result.overall_metrics["overall_accuracy"] == 1.0
        assert result.passed

    def test_sklearn_tabular_mode_missing_features_raises_clear_error(self, tmp_path):
        """Explicit tabular mode must fail loudly instead of falling back to text behavior."""
        model_path = tmp_path / "adult.joblib"
        model = DummyClassifier(strategy="most_frequent")
        model.fit(pd.DataFrame({"age": [24, 55], "hours-per-week": [35, 50]}), ["negative", "positive"])
        joblib.dump(model, model_path)

        evaluator = ClassificationEvaluator(
            str(model_path),
            {"evaluator": {"mode": "sklearn_tabular", "feature_columns": ["age", "hours-per-week"]}},
        )

        with pytest.raises(PredictionError) as exc_info:
            evaluator.predict([{"age": 42}])

        assert "configured feature columns" in str(exc_info.value)
        assert exc_info.value.details["required_feature_columns"] == ["age", "hours-per-week"]

    def test_unspecified_mode_guarded_fallback_uses_tabular_when_features_present(self, tmp_path):
        """When mode is omitted, sklearn tabular is only inferred with predict + configured columns."""
        model_path = tmp_path / "adult.joblib"
        model = DummyClassifier(strategy="constant", constant="positive")
        model.fit(pd.DataFrame({"age": [24, 55], "hours-per-week": [35, 50]}), ["negative", "positive"])
        joblib.dump(model, model_path)

        evaluator = ClassificationEvaluator(
            str(model_path),
            {"evaluator": {"feature_columns": ["age", "hours-per-week"]}},
        )
        evaluator.load_model()

        assert evaluator.predict([{"age": 42, "hours-per-week": 45}]) == ["positive"]

    def test_text_mode_backward_compatibility_with_seeded_payloads(self):
        """Backward-compatibility check for the original text/keyword demo path."""
        dataset = pd.DataFrame(
            {
                "id": ["1", "2", "3", "4"],
                "input": [
                    '{"text": "clearly positive stable example"}',
                    '{"text": "failed broken escalation example"}',
                    '{"text": "mostly positive production traffic"}',
                    '{"text": "ambiguous but still negative"}',
                ],
                "expected_label": ["positive", "negative", "positive", "negative"],
                "slice": ["easy", "critical", "typical", "edge_case"],
            }
        )
        evaluator = ClassificationEvaluator(
            "missing.json",
            {"evaluator": {"mode": "text"}, "gate": {"critical_slice_min_f1": 0.6}},
        )

        result = evaluator.evaluate(dataset, "text-compat")

        assert result.commit_sha == "text-compat"
        assert result.overall_metrics["overall_accuracy"] == 1.0
        assert result.passed
