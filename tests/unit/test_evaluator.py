import pandas as pd

from ares.evaluators.classification import ClassificationEvaluator
from ares.exceptions import DatasetSchemaError


def test_evaluator_validates_required_columns():
    evaluator = ClassificationEvaluator("missing.json")
    try:
        evaluator.evaluate(pd.DataFrame({"id": [1]}))
    except DatasetSchemaError:
        pass  # Expected
    else:
        raise AssertionError("expected DatasetSchemaError")


def test_classification_evaluator_runs():
    df = pd.DataFrame({"id": ["1"], "input": [{"label": "positive"}], "expected_label": ["positive"], "slice": ["critical"]})
    result = ClassificationEvaluator("missing.json").evaluate(df)
    assert result.passed
    assert result.overall_metrics["overall_accuracy"] == 1.0