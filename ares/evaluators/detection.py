from __future__ import annotations

from ares.evaluators.classification import ClassificationEvaluator


class DetectionEvaluator(ClassificationEvaluator):
    """Scaffold detection evaluator; defaults to classification-style label metrics."""