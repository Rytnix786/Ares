from __future__ import annotations

from ares.evaluators.distributed import evaluate_distributed, partition_rows


def test_distributed_evaluation_aggregates_1000_rows_across_4_workers() -> None:
    rows = [{"label": i % 2, "prediction": i % 2} for i in range(1000)]

    def evaluator(batch: list[dict[str, int]]) -> dict[str, float]:
        correct = sum(1 for row in batch if row["label"] == row["prediction"])
        return {"overall_accuracy": correct / len(batch), "overall_f1": correct / len(batch)}

    partitions = partition_rows(rows, workers=4)
    result = evaluate_distributed(rows, evaluator, workers=4)

    assert len(partitions) == 4
    assert sum(len(partition.rows) for partition in partitions) == 1000
    assert result["n_rows"] == 1000.0
    assert result["n_partitions"] == 4.0
    assert result["overall_accuracy"] == 1.0
    assert result["overall_f1"] == 1.0
