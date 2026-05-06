from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any


@dataclass(frozen=True)
class EvaluationPartition:
    index: int
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class PartitionResult:
    index: int
    n_rows: int
    metrics: dict[str, float]


def partition_rows(rows: Sequence[dict[str, Any]], workers: int) -> list[EvaluationPartition]:
    if workers <= 0:
        raise ValueError("workers must be positive")
    chunk_size = max(1, ceil(len(rows) / workers))
    return [EvaluationPartition(i, list(rows[i * chunk_size : (i + 1) * chunk_size])) for i in range(workers) if rows[i * chunk_size : (i + 1) * chunk_size]]


def aggregate_partition_results(results: Sequence[PartitionResult]) -> dict[str, float]:
    total = sum(result.n_rows for result in results)
    if total == 0:
        return {}
    metric_names = {name for result in results for name in result.metrics}
    return {
        name: sum(result.metrics.get(name, 0.0) * result.n_rows for result in results) / total
        for name in metric_names
    }


def evaluate_distributed(
    rows: Sequence[dict[str, Any]],
    evaluator: Callable[[list[dict[str, Any]]], dict[str, float]],
    workers: int = 4,
) -> dict[str, float]:
    partitions = partition_rows(rows, workers)
    results = [PartitionResult(part.index, len(part.rows), evaluator(part.rows)) for part in partitions]
    aggregated = aggregate_partition_results(results)
    aggregated["n_rows"] = float(sum(result.n_rows for result in results))
    aggregated["n_partitions"] = float(len(results))
    return aggregated
