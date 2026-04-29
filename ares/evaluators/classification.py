from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from ares.evaluators.base import BaseEvaluator
from ares.exceptions import ConfigurationInvalidError, ModelLoadError, PredictionError


TEXT_MODE = "text"
SKLEARN_TABULAR_MODE = "sklearn_tabular"
SUPPORTED_EVALUATOR_MODES = {TEXT_MODE, SKLEARN_TABULAR_MODE}


def _extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        raw = payload
        try:
            payload = ast.literal_eval(payload)
        except Exception:
            return raw.lower()
    if isinstance(payload, dict):
        return str(payload.get("text", "")).lower()
    return str(payload).lower()


def _parse_payload(payload: Any) -> Any:
    if not isinstance(payload, str):
        return payload
    try:
        return json.loads(payload)
    except Exception:
        try:
            return ast.literal_eval(payload)
        except Exception:
            return payload


def _keyword_features(text: str) -> list[float]:
    positive_keywords = ["positive", "great", "resolved", "stable", "clearly"]
    negative_keywords = ["negative", "failed", "broken", "escalation", "ambiguous"]
    return [
        float(len(text)),
        float(sum(keyword in text for keyword in positive_keywords)),
        float(sum(keyword in text for keyword in negative_keywords)),
    ]


class ClassificationEvaluator(BaseEvaluator):
    def _evaluator_config(self) -> dict[str, Any]:
        evaluator_config = self.config.get("evaluator", {}) if isinstance(self.config, dict) else {}
        return evaluator_config if isinstance(evaluator_config, dict) else {}

    def _configured_mode(self) -> str | None:
        mode = self._evaluator_config().get("mode")
        if mode is None:
            return None
        normalized = str(mode).strip().lower()
        if normalized not in SUPPORTED_EVALUATOR_MODES:
            raise ConfigurationInvalidError(
                "evaluator.mode",
                f"expected one of {sorted(SUPPORTED_EVALUATOR_MODES)}, got {mode!r}",
            )
        return normalized

    def _feature_columns(self) -> list[str]:
        raw_columns = self._evaluator_config().get("feature_columns", [])
        if raw_columns is None:
            return []
        if not isinstance(raw_columns, list):
            raise ConfigurationInvalidError(
                "evaluator.feature_columns",
                "expected a list of feature column names",
            )
        return [str(column) for column in raw_columns]

    def _label_mapping(self) -> dict[Any, str]:
        evaluator_config = self._evaluator_config()
        mapping: dict[Any, str] = {}
        if "positive_label" in evaluator_config:
            positive = str(evaluator_config["positive_label"])
            mapping.update({1: positive, "1": positive, True: positive, "true": positive, "True": positive})
        if "negative_label" in evaluator_config:
            negative = str(evaluator_config["negative_label"])
            mapping.update({0: negative, "0": negative, False: negative, "false": negative, "False": negative})
        return mapping

    def load_model(self) -> None:
        path = Path(self.model_path)
        if path.suffix == ".joblib" and path.is_file():
            try:
                self._model = joblib.load(path)
            except Exception as e:
                raise ModelLoadError(
                    model_path=str(path),
                    reason=str(e),
                ) from e
            return
        try:
            self._model = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
                "default_label": self.config.get("default_label", "positive"),
                "positive_keywords": ["positive", "great", "resolved", "stable", "clearly"],
                "negative_keywords": ["negative", "failed", "broken", "escalation", "ambiguous"],
            }
        except Exception as e:
            raise ModelLoadError(
                model_path=str(path),
                reason=str(e),
            ) from e

    def _has_sklearn_predict(self) -> bool:
        if hasattr(self._model, "predict"):
            return True
        if isinstance(self._model, dict):
            candidate = self._model.get("model")
            return hasattr(candidate, "predict")
        return False

    def _tabular_fallback_available(self, inputs: list[Any]) -> bool:
        if not self._has_sklearn_predict():
            return False
        feature_columns = self._feature_columns()
        if not feature_columns:
            return False
        try:
            self._build_tabular_frame(inputs, allow_missing=False)
        except PredictionError:
            return False
        return True

    def _resolve_mode(self, inputs: list[Any]) -> str:
        configured_mode = self._configured_mode()
        if configured_mode is not None:
            return configured_mode
        if self._tabular_fallback_available(inputs):
            return SKLEARN_TABULAR_MODE
        return TEXT_MODE

    def _build_tabular_frame(self, inputs: list[Any], *, allow_missing: bool = False) -> pd.DataFrame:
        feature_columns = self._feature_columns()
        if not feature_columns:
            raise PredictionError(
                reason="sklearn_tabular evaluator mode requires evaluator.feature_columns",
                details={"configured_feature_columns": feature_columns},
            )

        rows: list[dict[str, Any]] = []
        missing_by_row: dict[int, list[str]] = {}
        non_mapping_rows: list[int] = []
        for index, raw_item in enumerate(inputs):
            item = _parse_payload(raw_item)
            if isinstance(item, dict) and isinstance(item.get("features"), dict):
                item = item["features"]
            if not isinstance(item, dict):
                non_mapping_rows.append(index)
                if allow_missing:
                    rows.append({column: None for column in feature_columns})
                continue
            missing = [column for column in feature_columns if column not in item]
            if missing:
                missing_by_row[index] = missing
            rows.append({column: item.get(column) for column in feature_columns})

        if (missing_by_row or non_mapping_rows) and not allow_missing:
            raise PredictionError(
                reason="sklearn_tabular evaluator mode requires every payload to contain configured feature columns",
                details={
                    "required_feature_columns": feature_columns,
                    "missing_by_row": missing_by_row,
                    "non_mapping_rows": non_mapping_rows,
                },
            )
        return pd.DataFrame(rows, columns=feature_columns)

    def _predict_sklearn_tabular(self, inputs: list[Any]) -> list[Any]:
        if not self._has_sklearn_predict():
            raise PredictionError(
                reason="sklearn_tabular evaluator mode requires a loaded model with a predict method",
                details={"model_type": type(self._model).__name__},
            )
        frame = self._build_tabular_frame(inputs)
        model = self._model.get("model") if isinstance(self._model, dict) and "model" in self._model else self._model
        predictions = model.predict(frame)
        mapping = self._label_mapping()
        return [mapping.get(value, str(value)) for value in predictions]

    def _predict_text(self, inputs: list[Any]) -> list[Any]:
        if isinstance(self._model, dict) and {"model", "scaler"}.issubset(self._model):
            features = np.asarray([_keyword_features(_extract_text(item)) for item in inputs], dtype=float)
            scaled = self._model["scaler"].transform(features)
            return [str(value) for value in self._model["model"].predict(scaled)]
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

    def predict(self, inputs: list[Any]) -> list[Any]:
        if self._model is None:
            self.load_model()
        mode = self._resolve_mode(inputs)
        if mode == SKLEARN_TABULAR_MODE:
            return self._predict_sklearn_tabular(inputs)
        return self._predict_text(inputs)

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        labels = sorted({*map(str, predictions), *map(str, ground_truth)})
        average = "binary" if len(labels) == 2 else "macro"
        configured_positive = self._evaluator_config().get("positive_label")
        pos_label = str(configured_positive) if average == "binary" and configured_positive is not None else labels[-1] if average == "binary" else 1
        f1 = float(f1_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0))
        return {
            "overall_accuracy": float(accuracy_score(ground_truth, predictions)),
            "overall_f1": f1,
            "overall_precision": float(precision_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0)),
            "overall_recall": float(recall_score(ground_truth, predictions, average=average, pos_label=pos_label, zero_division=0)),
            "f1": f1,
        }