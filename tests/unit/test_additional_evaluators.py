from __future__ import annotations

import pandas as pd

from ares.evaluators.detection import DetectionEvaluator
from ares.evaluators.regression import RegressionEvaluator


def test_detection_evaluator_inherits_classification_behavior() -> None:
    df = pd.DataFrame(
        {
            "id": ["1", "2"],
            "input": ['{"text": "positive stable"}', '{"text": "negative failed"}'],
            "expected_label": ["positive", "negative"],
            "slice": ["easy", "critical"],
        }
    )
    result = DetectionEvaluator("missing.json", {"gate": {"critical_slice_min_f1": 0.5}}).evaluate(df)
    assert result.passed


def test_regression_evaluator_returns_numeric_metrics() -> None:
    evaluator = RegressionEvaluator("missing.json", {"constant": 1.0})
    predictions = evaluator.predict([{"value": 1.0}, {"value": 2.0}])
    metrics = evaluator.compute_metrics(predictions, [1.0, 2.0])
    assert set(metrics) == {"rmse", "mae", "r2"}