from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ares.evaluators.base import BaseEvaluator


class RegressionEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self._model = {"constant": float(self.config.get("constant", 0.0))}

    def predict(self, inputs: list[Any]) -> list[float]:
        if self._model is None:
            self.load_model()
        return [float(item.get("value", self._model["constant"])) if isinstance(item, dict) else self._model["constant"] for item in inputs]

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        return {"rmse": float(np.sqrt(mean_squared_error(ground_truth, predictions))), "mae": float(mean_absolute_error(ground_truth, predictions)), "r2": float(r2_score(ground_truth, predictions))}