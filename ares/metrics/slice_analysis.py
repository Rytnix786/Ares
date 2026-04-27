from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SliceResult:
    slice_name: str
    n_samples: int
    metrics: dict[str, float]
    is_critical: bool
    passed_critical_threshold: bool


def evaluate_slices(df: pd.DataFrame, predictions: list[Any], slice_column: str = "slice", critical_slices: list[str] | None = None, critical_threshold: float = 0.60, metric_fn: Callable[[list[Any], list[Any]], dict[str, float]] | None = None) -> dict[str, SliceResult]:
    if metric_fn is None:
        raise ValueError("metric_fn is required")
    if slice_column not in df.columns:
        raise ValueError(f"missing slice column: {slice_column}")
    critical_slices = critical_slices or ["critical", "edge_case"]
    results: dict[str, SliceResult] = {}
    for slice_name in df[slice_column].dropna().unique():
        mask = (df[slice_column] == slice_name).tolist()
        slice_df = df[df[slice_column] == slice_name]
        slice_preds = [p for p, keep in zip(predictions, mask, strict=False) if keep]
        metrics = metric_fn(slice_preds, slice_df["expected_label"].tolist())
        primary_metric = float(metrics.get("f1", metrics.get("overall_f1", next(iter(metrics.values())) if metrics else 0.0)))
        is_critical = str(slice_name) in critical_slices
        results[str(slice_name)] = SliceResult(str(slice_name), len(slice_df), metrics, is_critical, primary_metric >= critical_threshold if is_critical else True)
    return results