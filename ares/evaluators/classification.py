from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from ares.evaluators.base import BaseEvaluator


class ClassificationEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        path = Path(self.model_path)
        self._model = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
            "default_label": self.config.get("default_label", "positive"),
            "positive_keywords": ["positive", "great", "resolved", "stable", "clearly"],
            "negative_keywords": ["negative", "failed", "broken", "escalation", "ambiguous"],
        }

    def predict(self, inputs: list[Any]) -> list[Any]:
        label = self._model.get("default_label", "positive") if isinstance(self._model, dict) else "positive"
        positive_keywords = [str(item).lower() for item in self._model.get("positive_keywords", ["positive"])] if isinstance(self._model, dict) else ["positive"]
        negative_keywords = [str(item).lower() for item in self._model.get("negative_keywords", ["negative"])] if isinstance(self._model, dict) else ["negative"]
        parsed = []
        for item in inputs:
            if isinstance(item, str):
                try:
                    item = ast.literal_eval(item)
                except Exception:
                    item = {}
            if isinstance(item, dict):
                if "label" in item:
                    parsed.append(str(item["label"]))
                    continue
                text = str(item.get("text", "")).lower()
                if any(keyword in text for keyword in negative_keywords):
                    parsed.append("negative")
                    continue
                if any(keyword in text for keyword in positive_keywords):
                    parsed.append("positive")
                    continue
            parsed.append(label)
        return parsed

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        labels = sorted({*map(str, predictions), *map(str, ground_truth)})
        average = "binary" if len(labels) == 2 else "macro"
        pos_label = labels[-1] if average == "binary" else 1
        f1 = float(f1_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0))
        return {
            "overall_accuracy": float(accuracy_score(ground_truth, predictions)),
            "overall_f1": f1,
            "overall_precision": float(precision_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0)),
            "overall_recall": float(recall_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0)),
            "f1": f1,
        }