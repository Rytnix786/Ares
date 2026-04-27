#!/usr/bin/env python3
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from ares.config import load_ares_config, settings
from ares.db import crud
from ares.db.session import get_sessionmaker
from ares.evaluators.classification import ClassificationEvaluator


def extract_text(payload: Any) -> str:
    if isinstance(payload, str):
        try:
            payload = ast.literal_eval(payload)
        except Exception:
            return payload.lower()
    if isinstance(payload, dict):
        return str(payload.get("text", "")).lower()
    return str(payload).lower()


def build_features(series: pd.Series) -> list[list[float]]:
    positive_keywords = ["positive", "great", "resolved", "stable", "clearly"]
    negative_keywords = ["negative", "failed", "broken", "escalation", "ambiguous"]
    rows: list[list[float]] = []
    for value in series.tolist():
        text = extract_text(value)
        rows.append(
            [
                float(len(text)),
                float(sum(keyword in text for keyword in positive_keywords)),
                float(sum(keyword in text for keyword in negative_keywords)),
            ]
        )
    return rows


def train_baseline_model(train_path: Path, model_path: Path) -> float:
    dataset = pd.read_csv(train_path)
    features = np.asarray(build_features(dataset["input"]), dtype=float)
    labels = dataset["expected_label"].astype(str).tolist()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(scaled, labels)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"scaler": scaler, "model": model}, model_path)
    return round(model_path.stat().st_size / (1024 * 1024), 6)


async def register_baseline(model_path: Path, *, model_size_mb: float) -> str:
    config = load_ares_config()
    val_df = pd.read_csv("data/golden_set/val.csv")
    evaluation = ClassificationEvaluator(str(model_path), config).evaluate(val_df, commit_sha="baseline-seed")
    run_id = "baseline-seed-run"
    async with get_sessionmaker()() as session:
        async with session.begin():
            await crud.create_evaluation_run(
                session,
                id=run_id,
                commit_sha="baseline-seed",
                model_name="baseline",
                model_version="champion_v1",
                branch="main",
                pr_number=None,
                overall_f1=float(evaluation.overall_metrics.get("overall_f1", 0.0)),
                overall_accuracy=float(evaluation.overall_metrics.get("overall_accuracy", 0.0)),
                overall_precision=float(evaluation.overall_metrics.get("overall_precision", 0.0)),
                overall_recall=float(evaluation.overall_metrics.get("overall_recall", 0.0)),
                latency_p50_ms=evaluation.latency_p50_ms,
                latency_p99_ms=evaluation.latency_p99_ms,
                model_size_mb=model_size_mb,
                slice_metrics=evaluation.slice_metrics,
                gate_config_snapshot=config.get("gate", {}),
                metadata_json={"artifact_path": str(model_path)},
                passed=evaluation.passed,
                failure_reason=evaluation.failure_reason,
                golden_set_version=settings.GOLDEN_SET_VERSION,
                n_samples_evaluated=len(val_df),
                duration_seconds=0.0,
                mlflow_run_id=None,
                artifact_uri=str(model_path),
                mlflow_status="seeded",
                mlflow_error=None,
            )
        await crud.promote_champion(session, "baseline", run_id, "seed_champion", "Initial baseline champion")
    return run_id


async def main() -> None:
    train_path = Path("data/golden_set/train.csv")
    model_path = Path("models/baseline/champion_v1.joblib")
    model_size_mb = train_baseline_model(train_path, model_path)
    run_id = await register_baseline(model_path, model_size_mb=model_size_mb)
    print(run_id)


if __name__ == "__main__":
    asyncio.run(main())
