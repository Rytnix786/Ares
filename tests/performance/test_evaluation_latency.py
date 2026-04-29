from __future__ import annotations

import pandas as pd
import pytest

from ares.evaluators.classification import ClassificationEvaluator


@pytest.mark.performance
def test_classification_evaluation_latency(benchmark: pytest.FixtureRequest) -> None:
    dataset = pd.DataFrame(
        {
            "id": [str(index) for index in range(25)],
            "input": [{"label": "positive"} for _ in range(25)],
            "expected_label": ["positive" for _ in range(25)],
            "slice": ["critical" for _ in range(25)],
        }
    )
    evaluator = ClassificationEvaluator("models/candidate.json")

    result = benchmark(evaluator.evaluate, dataset, "benchmark")

    assert result.overall_metrics["overall_f1"] >= 0.0
