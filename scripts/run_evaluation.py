#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy.exc import IntegrityError

try:
    import mlflow
except ModuleNotFoundError:  # pragma: no cover
    mlflow = None

try:
    import structlog
except ModuleNotFoundError:  # pragma: no cover
    structlog = None

from ares.config import load_ares_config, settings
from ares.db import crud
from ares.db.session import dispose_engine, get_sessionmaker
from ares.evaluators.classification import ClassificationEvaluator
from ares.gate.rules_engine import evaluate as evaluate_gate
from ares.gate.rules_engine import snapshot_gate_config
from ares.golden_set import validate_golden_set
from ares.logging import configure_logging

configure_logging()
struct_logger = structlog.get_logger(__name__) if structlog is not None else None
std_logger = logging.getLogger(__name__)


def log_info(message: str, **kwargs: object) -> None:
    if struct_logger is not None:
        struct_logger.info(message, **kwargs)
    else:
        std_logger.info("%s %s", message, kwargs)


def log_warning(message: str, **kwargs: object) -> None:
    if struct_logger is not None:
        struct_logger.warning(message, **kwargs)
    else:
        std_logger.warning("%s %s", message, kwargs)


def log_exception(message: str, **kwargs: object) -> None:
    if struct_logger is not None:
        struct_logger.exception(message, **kwargs)
    else:
        std_logger.exception("%s %s", message, kwargs)


def failure_payload(exc: BaseException) -> dict[str, Any]:
    return {
        "passed": False,
        "run_id": None,
        "details_url": None,
        "metric_table": {},
        "slice_regressions": [],
        "failure_reason": str(exc),
        "error_type": type(exc).__name__,
    }


def extract_metrics_for_gate(run_like: Any) -> dict[str, float]:
    if run_like is None:
        return {}
    return {
        "overall_f1": float(getattr(run_like, "overall_f1", 0.0)),
        "overall_accuracy": float(getattr(run_like, "overall_accuracy", 0.0)),
        "overall_precision": float(getattr(run_like, "overall_precision", 0.0)),
        "overall_recall": float(getattr(run_like, "overall_recall", 0.0)),
        "latency_p99_ms": float(getattr(run_like, "latency_p99_ms", 0.0)),
        "model_size_mb": float(getattr(run_like, "model_size_mb", 0.0)),
    }


def build_metric_table(candidate_metrics: dict[str, float], champion_metrics: dict[str, float]) -> dict[str, dict[str, float]]:
    keys = sorted(set(candidate_metrics) | set(champion_metrics))
    return {
        key: {
            "champion": float(champion_metrics.get(key, 0.0)),
            "candidate": float(candidate_metrics.get(key, 0.0)),
            "delta": float(candidate_metrics.get(key, 0.0)) - float(champion_metrics.get(key, 0.0)),
        }
        for key in keys
    }


def maybe_run_deepchecks(dataset: pd.DataFrame, predictions: list[Any], enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"status": "skipped", "reason": "disabled"}
    try:
        from deepchecks.tabular import Dataset
        from deepchecks.tabular.checks.model_evaluation import (
            ConfusionMatrixReport,
            TrainTestPerformance,
            WeakSegmentsPerformance,
        )
    except Exception as exc:  # pragma: no cover
        return {"status": "skipped", "reason": f"deepchecks unavailable: {exc}"}

    features = pd.DataFrame(
        {
            "text_length": dataset["input"].astype(str).str.len(),
            "difficulty": dataset.get("difficulty", pd.Series([0] * len(dataset))),
            "expected_label": dataset["expected_label"].tolist(),
        }
    )
    data = Dataset(features, label="expected_label")

    class StaticModel:
        def __init__(self, values: list[Any]):
            self.values = [str(value) for value in values]

        def predict(self, X):
            return self.values[: len(X)]

    model = StaticModel(predictions)
    checks = [ConfusionMatrixReport(), TrainTestPerformance(), WeakSegmentsPerformance()]
    executed: list[dict[str, Any]] = []
    for check in checks:
        try:
            if isinstance(check, TrainTestPerformance):
                check.run(train_dataset=data, test_dataset=data, model=cast(Any, model))
            else:
                check.run(dataset=data, model=cast(Any, model))
            executed.append({"check": check.__class__.__name__, "status": "ok"})
        except Exception as exc:  # pragma: no cover
            executed.append({"check": check.__class__.__name__, "status": "failed", "reason": str(exc)})
    return {"status": "completed", "checks": executed}


def resolve_dataset_path(args: argparse.Namespace) -> Path:
    if args.dataset_path:
        return Path(args.dataset_path)
    return Path("data/golden_set") / f"{args.split}.csv"


def compute_model_size_mb(model_path: str) -> float:
    path = Path(model_path)
    if not path.is_file():
        return 0.0
    return round(path.stat().st_size / (1024 * 1024), 6)


async def fetch_champion_metrics(model_name: str) -> tuple[dict[str, float], Any | None]:
    async with get_sessionmaker()() as session:
        champion = await crud.get_active_champion(session, model_name)
        if champion is None:
            return {}, None
        champion_run = await crud.get_evaluation_run(session, champion.champion_run_id)
        return extract_metrics_for_gate(champion_run), champion_run


async def get_cached_run(commit_sha: str, model_name: str) -> Any | None:
    async with get_sessionmaker()() as session:
        return await crud.get_cached_evaluation(session, commit_sha, settings.GOLDEN_SET_VERSION, model_name)


async def persist_run(values: dict[str, Any]) -> Any:
    async with get_sessionmaker()() as session:
        try:
            async with session.begin():
                cached = await crud.get_cached_evaluation(session, values["commit_sha"], values["golden_set_version"], values["model_name"])
                if cached is not None:
                    return cached
                return await crud.create_evaluation_run(session, **values)
        except IntegrityError:
            await session.rollback()
            cached = await crud.get_cached_evaluation(session, values["commit_sha"], values["golden_set_version"], values["model_name"])
            if cached is None:
                raise
            return cached


def payload_from_run(run: Any, champion_metrics: dict[str, float] | None = None) -> dict[str, Any]:
    champion_metrics = champion_metrics or {}
    candidate_metrics = extract_metrics_for_gate(run)
    return {
        "passed": bool(run.passed),
        "run_id": run.id,
        "details_url": f"{settings.ARES_DASHBOARD_URL}/drill-down?run_id={run.id}",
        "metric_table": build_metric_table(candidate_metrics, champion_metrics),
        "slice_regressions": [
            {"slice": name, "candidate_f1": float(metrics.get("f1", metrics.get("overall_f1", 0.0)))}
            for name, metrics in (run.slice_metrics or {}).items()
            if isinstance(metrics, dict) and not metrics.get("passed_critical_threshold", True)
        ],
        "failure_reason": run.failure_reason,
        "gate_config_snapshot": run.gate_config_snapshot,
        "duration_seconds": run.duration_seconds,
        "mlflow_run_id": run.mlflow_run_id,
        "artifact_uri": run.artifact_uri,
        "mlflow_status": getattr(run, "mlflow_status", "pending"),
    }


def log_with_mlflow(
    run_name: str,
    metadata: dict[str, Any],
    candidate_metrics: dict[str, float],
    dataset: pd.DataFrame,
    predictions: list[Any],
    payload: dict[str, Any],
) -> tuple[str | None, str | None, str, str | None]:
    if mlflow is None:
        return None, None, "skipped", "mlflow is not installed"
    if not os.getenv("MLFLOW_TRACKING_URI"):
        return None, None, "skipped", "MLFLOW_TRACKING_URI not set"

    try:
        if settings.MLFLOW_TRACKING_URI:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment("ares-evaluations")
        with tempfile.TemporaryDirectory() as temp_dir:
            predictions_path = Path(temp_dir) / "predictions.csv"
            summary_path = Path(temp_dir) / "summary.json"
            artifact_df = dataset[["id", "expected_label", "slice"]].copy()
            artifact_df["prediction"] = predictions
            artifact_df.to_csv(predictions_path, index=False)
            summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            with mlflow.start_run(run_name=run_name) as active_run:
                mlflow.log_params({k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))})
                mlflow.log_metrics({k: float(v) for k, v in candidate_metrics.items() if isinstance(v, (int, float))})
                mlflow.log_artifact(str(predictions_path), artifact_path="predictions")
                mlflow.log_artifact(str(summary_path), artifact_path="summaries")
                return active_run.info.run_id, active_run.info.artifact_uri, "logged", None
    except Exception as exc:  # pragma: no cover
        log_warning("mlflow_logging_failed", error=str(exc))
        return None, None, "failed", str(exc)


async def evaluate_once(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        cached = await get_cached_run(args.commit_sha, args.model_name)
        if cached is not None:
            return payload_from_run(cached), 0 if cached.passed else 1

        start = time.perf_counter()
        config = load_ares_config()
        dataset_path = resolve_dataset_path(args)
        dataset = pd.read_csv(dataset_path)
        validation_summary = validate_golden_set(dataset, dataset_path, args.split, config)
        evaluator = ClassificationEvaluator(args.model_path, config)
        evaluation_result = evaluator.evaluate(dataset, commit_sha=args.commit_sha)

        champion_metrics, _champion_run = await fetch_champion_metrics(args.model_name)
        candidate_metrics = {
            **{k: float(v) for k, v in evaluation_result.overall_metrics.items() if isinstance(v, (int, float))},
            "latency_p99_ms": evaluation_result.latency_p99_ms,
            "model_size_mb": compute_model_size_mb(args.model_path),
        }
        gate_config = snapshot_gate_config(config)
        gate_decision = (
            evaluate_gate(candidate_metrics, champion_metrics, evaluation_result.slice_metrics, config, len(dataset))
            if champion_metrics
            else None
        )
        passed = bool(evaluation_result.passed and (gate_decision.passed if gate_decision else True))
        failure_reason = None if passed else (gate_decision.reason if gate_decision else evaluation_result.failure_reason)
        slice_regressions = gate_decision.slice_regressions if gate_decision else [
            {"slice": name, "candidate_f1": float(metrics.get("f1", metrics.get("overall_f1", 0.0)))}
            for name, metrics in evaluation_result.slice_metrics.items()
            if not metrics.get("passed_critical_threshold", True)
        ]

        run_id = str(uuid.uuid4())
        details_url = f"{settings.ARES_DASHBOARD_URL}/drill-down?run_id={run_id}"
        deepchecks_summary = maybe_run_deepchecks(dataset, evaluation_result.raw_predictions, args.run_deepchecks)
        duration_seconds = time.perf_counter() - start
        payload = {
            "passed": passed,
            "run_id": run_id,
            "details_url": details_url,
            "metric_table": build_metric_table(candidate_metrics, champion_metrics),
            "slice_regressions": slice_regressions,
            "failure_reason": failure_reason,
            "gate_config_snapshot": gate_config,
            "duration_seconds": duration_seconds,
        }

        mlflow_run_id, artifact_uri, mlflow_status, mlflow_error = log_with_mlflow(
            run_name=f"{args.model_name}-{args.commit_sha[:12]}",
            metadata={
                "model_name": args.model_name,
                "model_version": args.model_version,
                "commit_sha": args.commit_sha,
                "split": args.split,
                "golden_set_version": settings.GOLDEN_SET_VERSION,
                "passed": passed,
            },
            candidate_metrics=candidate_metrics,
            dataset=dataset,
            predictions=evaluation_result.raw_predictions,
            payload=payload,
        )
        payload["mlflow_run_id"] = mlflow_run_id
        payload["artifact_uri"] = artifact_uri
        payload["mlflow_status"] = mlflow_status

        run = await persist_run(
            {
                "id": run_id,
                "commit_sha": args.commit_sha,
                "model_name": args.model_name,
                "model_version": args.model_version,
                "branch": os.getenv("GITHUB_REF_NAME", os.getenv("BRANCH_NAME", "unknown")),
                "pr_number": args.pr_number,
                "overall_f1": float(candidate_metrics.get("overall_f1", 0.0)),
                "overall_accuracy": float(candidate_metrics.get("overall_accuracy", 0.0)),
                "overall_precision": float(candidate_metrics.get("overall_precision", 0.0)),
                "overall_recall": float(candidate_metrics.get("overall_recall", 0.0)),
                "latency_p50_ms": evaluation_result.latency_p50_ms,
                "latency_p99_ms": evaluation_result.latency_p99_ms,
                "model_size_mb": float(candidate_metrics.get("model_size_mb", 0.0)),
                "slice_metrics": evaluation_result.slice_metrics,
                "gate_config_snapshot": gate_config,
                "metadata_json": {
                    "split": args.split,
                    "validation": validation_summary,
                    "deepchecks": deepchecks_summary,
                    "details_url": details_url,
                    "dataset_path": str(dataset_path),
                },
                "passed": passed,
                "failure_reason": failure_reason,
                "golden_set_version": settings.GOLDEN_SET_VERSION,
                "n_samples_evaluated": len(dataset),
                "duration_seconds": duration_seconds,
                "mlflow_run_id": mlflow_run_id,
                "artifact_uri": artifact_uri,
                "mlflow_status": mlflow_status,
                "mlflow_error": mlflow_error,
            }
        )
        stored_payload = payload_from_run(run, champion_metrics)
        stored_payload["validation"] = validation_summary
        stored_payload["deepchecks"] = deepchecks_summary
        return stored_payload, 0 if run.passed else 1
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--model-name", default="default-model")
    parser.add_argument("--model-version", default="candidate")
    parser.add_argument("--split", choices=["val", "test"], default="val")
    parser.add_argument("--dataset-path")
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--run-deepchecks", action="store_true")
    args = parser.parse_args()
    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload, exit_code = asyncio.run(evaluate_once(args))
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log_info("evaluation_complete", commit_sha=args.commit_sha, model_name=args.model_name, passed=payload["passed"])
        return exit_code
    except Exception as exc:
        log_exception("evaluation_failed", error=str(exc))
        output.write_text(json.dumps(failure_payload(exc), indent=2), encoding="utf-8")
        return 1


if __name__ == "__main__":
    sys.exit(main())