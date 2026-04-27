from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from statistics import median
from typing import Any

import numpy as np
import pandas as pd

from ares.metrics.slice_analysis import evaluate_slices


@dataclass(frozen=True)
class EvaluationResult:
    model_id: str
    commit_sha: str
    overall_metrics: dict[str, float]
    slice_metrics: dict[str, dict[str, float | bool | int]]
    latency_p50_ms: float
    latency_p99_ms: float
    passed: bool
    failure_reason: str | None
    raw_predictions: list[Any]


class BaseEvaluator(ABC):
    required_columns = {"id", "input", "expected_label", "slice"}

    def __init__(self, model_path: str, config: dict[str, Any] | None = None):
        self.model_path = model_path
        self.config = config or {}
        self._model: Any = None

    @abstractmethod
    def load_model(self) -> None: ...

    @abstractmethod
    def predict(self, inputs: list[Any]) -> list[Any]: ...

    @abstractmethod
    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]: ...

    def evaluate(self, dataset: pd.DataFrame, commit_sha: str = "local") -> EvaluationResult:
        missing = self.required_columns - set(dataset.columns)
        if missing:
            raise ValueError(f"missing required dataset columns: {sorted(missing)}")
        if self._model is None:
            self.load_model()
        gate_config = self.config.get("gate", {}) if isinstance(self.config, dict) else {}
        critical_threshold = float(gate_config.get("critical_slice_min_f1", 0.60))
        start = time.perf_counter()
        predictions = self.predict(dataset["input"].tolist())
        elapsed_ms = (time.perf_counter() - start) * 1000
        if len(predictions) != len(dataset):
            raise ValueError("prediction count does not match dataset rows")
        latencies = [elapsed_ms / max(len(predictions), 1)] * len(predictions)
        overall = self.compute_metrics(predictions, dataset["expected_label"].tolist())
        slices = evaluate_slices(dataset, predictions, metric_fn=self.compute_metrics, critical_threshold=critical_threshold)
        slice_payload = {k: {"n_samples": v.n_samples, "is_critical": v.is_critical, "passed_critical_threshold": v.passed_critical_threshold, **v.metrics} for k, v in slices.items()}
        passed = all(bool(v["passed_critical_threshold"]) for v in slice_payload.values())
        return EvaluationResult(self.model_path, commit_sha, overall, slice_payload, float(median(latencies)), float(np.percentile(latencies, 99)), passed, None if passed else "critical slice threshold failed", predictions)