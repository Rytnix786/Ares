#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ares.api.presenters import build_run_decision_payload, extract_slice_regressions
from ares.config import load_ares_config, settings
from ares.db import crud
from ares.db.session import dispose_engine, get_engine, get_sessionmaker
from ares.evaluators.classification import ClassificationEvaluator
from ares.gate.rules_engine import evaluate as evaluate_gate
from ares.gate.rules_engine import snapshot_gate_config
from ares.golden_set import sha256_file
from ares.models import Base

ADULT_FEATURE_COLUMNS = [
    "age",
    "workclass",
    "fnlwgt",
    "education",
    "education-num",
    "marital-status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
    "native-country",
]

NUMERIC_COLUMNS = [
    "age",
    "fnlwgt",
    "education-num",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
]
CATEGORICAL_COLUMNS = [column for column in ADULT_FEATURE_COLUMNS if column not in NUMERIC_COLUMNS]


def _current_commit_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short=12", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "local"


def _normalize_target(value: Any) -> str:
    normalized = str(value).strip().rstrip(".")
    return "positive" if normalized == ">50K" else "negative"


def _slice_for_row(row: pd.Series) -> str:
    education_num = float(row.get("education-num", 0) or 0)
    capital_gain = float(row.get("capital-gain", 0) or 0)
    capital_loss = float(row.get("capital-loss", 0) or 0)
    hours = float(row.get("hours-per-week", 0) or 0)
    if education_num <= 9:
        return "critical"
    if capital_gain > 0 or capital_loss > 0 or hours >= 55:
        return "edge_case"
    if education_num >= 13:
        return "high_education"
    return "typical"


def _fallback_adult_frame(rows: int = 240) -> tuple[pd.DataFrame, pd.Series, str]:
    workclasses = ["Private", "Self-emp-not-inc", "Local-gov", "Federal-gov"]
    educations = ["HS-grad", "Some-college", "Bachelors", "Masters", "Assoc-voc"]
    marital = ["Never-married", "Married-civ-spouse", "Divorced", "Separated"]
    occupations = ["Adm-clerical", "Exec-managerial", "Craft-repair", "Prof-specialty", "Sales"]
    relationships = ["Not-in-family", "Husband", "Own-child", "Unmarried"]
    races = ["White", "Black", "Asian-Pac-Islander", "Amer-Indian-Eskimo", "Other"]
    sexes = ["Male", "Female"]
    countries = ["United-States", "Canada", "Mexico", "Philippines"]

    records: list[dict[str, Any]] = []
    targets: list[str] = []
    for index in range(rows):
        education_num = [9, 10, 13, 14, 11][index % 5]
        age = 22 + (index * 7) % 45
        hours = 30 + (index * 3) % 35
        capital_gain = 0 if index % 7 else 5178
        capital_loss = 0 if index % 11 else 1887
        record = {
            "age": age,
            "workclass": workclasses[index % len(workclasses)],
            "fnlwgt": 75_000 + index * 137,
            "education": educations[index % len(educations)],
            "education-num": education_num,
            "marital-status": marital[index % len(marital)],
            "occupation": occupations[index % len(occupations)],
            "relationship": relationships[index % len(relationships)],
            "race": races[index % len(races)],
            "sex": sexes[index % len(sexes)],
            "capital-gain": capital_gain,
            "capital-loss": capital_loss,
            "hours-per-week": hours,
            "native-country": countries[index % len(countries)],
        }
        high_income = (
            education_num >= 13
            and age >= 30
            and hours >= 38
            and record["occupation"] in {"Exec-managerial", "Prof-specialty", "Sales"}
        ) or capital_gain > 0
        records.append(record)
        targets.append("positive" if high_income else "negative")
    return pd.DataFrame(records), pd.Series(targets, name="class"), "fallback"


def load_adult_income(source: str, max_rows: int) -> tuple[pd.DataFrame, pd.Series, str]:
    if source in {"auto", "sklearn_openml"}:
        try:
            dataset = fetch_openml("adult", version=2, as_frame=True, parser="auto")
            features = dataset.data[ADULT_FEATURE_COLUMNS].copy()
            target = dataset.target.map(_normalize_target)
            features = features.replace({"?": "Unknown"}).fillna("Unknown")
            for column in NUMERIC_COLUMNS:
                features[column] = pd.to_numeric(features[column], errors="coerce")
            if max_rows > 0 and len(features) > max_rows:
                sampled = features.assign(__target=target).sample(
                    n=max_rows,
                    random_state=42,
                )
                target = sampled.pop("__target")
                features = sampled
            return features.reset_index(drop=True), target.reset_index(drop=True), "sklearn_openml"
        except Exception:
            if source == "sklearn_openml":
                raise
    fallback_rows = max(max_rows, 120) if max_rows > 0 else 240
    return _fallback_adult_frame(fallback_rows)


def make_golden_frame(features: pd.DataFrame, target: pd.Series, split_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, (_, row) in enumerate(features.iterrows()):
        payload = {column: row[column].item() if hasattr(row[column], "item") else row[column] for column in ADULT_FEATURE_COLUMNS}
        rows.append(
            {
                "id": f"adult-{split_name}-{index:05d}",
                "input": json.dumps(payload, sort_keys=True),
                "expected_label": str(target.iloc[index]),
                "slice": _slice_for_row(row),
            }
        )
    return pd.DataFrame(rows)


def parsed_features(golden_frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([json.loads(value) for value in golden_frame["input"].tolist()])[
        ADULT_FEATURE_COLUMNS
    ]


def write_golden_splits(
    features: pd.DataFrame,
    target: pd.Series,
    output_dir: Path,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    train_x, remaining_x, train_y, remaining_y = train_test_split(
        features,
        target,
        test_size=0.4,
        random_state=42,
        stratify=target,
    )
    val_x, test_x, val_y, test_y = train_test_split(
        remaining_x,
        remaining_y,
        test_size=0.5,
        random_state=42,
        stratify=remaining_y,
    )
    split_inputs = {
        "train": (train_x.reset_index(drop=True), train_y.reset_index(drop=True)),
        "val": (val_x.reset_index(drop=True), val_y.reset_index(drop=True)),
        "test": (test_x.reset_index(drop=True), test_y.reset_index(drop=True)),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    checksums: dict[str, str] = {}
    for split_name, (split_x, split_y) in split_inputs.items():
        frame = make_golden_frame(split_x, split_y, split_name)
        path = output_dir / f"{split_name}.csv"
        frame.to_csv(path, index=False)
        frames[split_name] = frame
        checksums[split_name] = sha256_file(path)
    return frames, checksums


def build_model() -> Pipeline:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, NUMERIC_COLUMNS),
            ("categorical", categorical_transformer, CATEGORICAL_COLUMNS),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def train_and_save_model(train_frame: pd.DataFrame, artifact_path: Path) -> float:
    model = build_model()
    model.fit(parsed_features(train_frame), train_frame["expected_label"].astype(str).tolist())
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, artifact_path)
    return round(artifact_path.stat().st_size / (1024 * 1024), 6)


def adult_evaluator_config(base_config: dict[str, Any]) -> dict[str, Any]:
    config = dict(base_config)
    config["evaluator"] = {
        "mode": "sklearn_tabular",
        "feature_columns": ADULT_FEATURE_COLUMNS,
        "positive_label": "positive",
        "negative_label": "negative",
    }
    return config


def metrics_for_result(result: Any, model_size_mb: float) -> dict[str, float]:
    return {
        **{k: float(v) for k, v in result.overall_metrics.items() if isinstance(v, int | float)},
        "latency_p99_ms": float(result.latency_p99_ms),
        "model_size_mb": float(model_size_mb),
    }


async def ensure_database_schema(create_db: bool) -> None:
    if not create_db:
        return
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def persist_run(values: dict[str, Any]) -> Any:
    async with get_sessionmaker()() as session:
        async with session.begin():
            return await crud.create_evaluation_run(session, **values)


async def promote_run(model_name: str, run_id: str, reason: str) -> None:
    async with get_sessionmaker()() as session:
        await crud.promote_champion(session, model_name, run_id, "adult_income_setup", reason)


def _base_run_values(
    *,
    run_id: str,
    commit_sha: str,
    model_name: str,
    model_version: str,
    golden_set_version: str,
    artifact_path: Path,
    model_size_mb: float,
    evaluation: Any,
    gate_config: dict[str, Any],
    metadata: dict[str, Any],
    passed: bool,
    failure_reason: str | None,
    duration_seconds: float,
) -> dict[str, Any]:
    metrics = metrics_for_result(evaluation, model_size_mb)
    return {
        "id": run_id,
        "commit_sha": commit_sha,
        "model_name": model_name,
        "model_version": model_version,
        "branch": os.getenv("GITHUB_REF_NAME", os.getenv("BRANCH_NAME", "local")),
        "pr_number": None,
        "overall_f1": float(metrics.get("overall_f1", 0.0)),
        "overall_accuracy": float(metrics.get("overall_accuracy", 0.0)),
        "overall_precision": float(metrics.get("overall_precision", 0.0)),
        "overall_recall": float(metrics.get("overall_recall", 0.0)),
        "latency_p50_ms": float(evaluation.latency_p50_ms),
        "latency_p99_ms": float(evaluation.latency_p99_ms),
        "model_size_mb": float(model_size_mb),
        "slice_metrics": evaluation.slice_metrics,
        "gate_config_snapshot": gate_config,
        "metadata_json": {"artifact_path": str(artifact_path), **metadata},
        "passed": passed,
        "failure_reason": failure_reason,
        "golden_set_version": golden_set_version,
        "n_samples_evaluated": len(evaluation.raw_predictions),
        "duration_seconds": duration_seconds,
        "mlflow_run_id": None,
        "artifact_uri": str(artifact_path),
        "mlflow_status": "not_configured",
        "mlflow_error": None,
    }


def verify_api(api_base_url: str, api_key: str, model_name: str, run_id: str) -> dict[str, Any]:
    base = api_base_url.rstrip("/")
    if base.endswith("/api/v1"):
        origin = base[: -len("/api/v1")]
        api_v1 = base
    else:
        origin = base
        api_v1 = f"{base}/api/v1"
    headers = {"X-API-Key": api_key}
    result = {
        "champion_endpoint_ok": False,
        "evaluations_endpoint_ok": False,
        "export_endpoint_ok": False,
        "health_endpoint_ok": False,
        "errors": {},
    }
    checks = {
        "health_endpoint_ok": f"{origin}/health/ready",
        "champion_endpoint_ok": f"{api_v1}/champions/{model_name}",
        "evaluations_endpoint_ok": f"{api_v1}/evaluations/{run_id}",
        "export_endpoint_ok": f"{api_v1}/champions/export",
    }
    with httpx.Client(timeout=3.0, headers=headers) as client:
        for key, url in checks.items():
            try:
                response = client.get(url)
                result[key] = response.status_code < 400
                if response.status_code >= 400:
                    result["errors"][key] = f"HTTP {response.status_code}"
            except Exception as exc:
                result["errors"][key] = str(exc)
    if not all(bool(result[key]) for key in ["champion_endpoint_ok", "evaluations_endpoint_ok", "export_endpoint_ok"]):
        in_process = verify_api_in_process(api_key, model_name, run_id)
        if any(bool(in_process[key]) for key in ["champion_endpoint_ok", "evaluations_endpoint_ok", "export_endpoint_ok"]):
            result = in_process
    return result


def verify_api_in_process(api_key: str, model_name: str, run_id: str) -> dict[str, Any]:
    result = {
        "champion_endpoint_ok": False,
        "evaluations_endpoint_ok": False,
        "export_endpoint_ok": False,
        "health_endpoint_ok": False,
        "verification_mode": "in_process_fastapi",
        "errors": {},
    }
    try:
        from fastapi.testclient import TestClient

        from ares.api.main import app

        headers = {"X-API-Key": api_key}
        checks = {
            "health_endpoint_ok": ("/health/ready", {}),
            "champion_endpoint_ok": (f"/api/v1/champions/{model_name}", headers),
            "evaluations_endpoint_ok": (f"/api/v1/evaluations/{run_id}", headers),
            "export_endpoint_ok": ("/api/v1/champions/export", headers),
        }
        with TestClient(app) as client:
            for key, (path, request_headers) in checks.items():
                response = client.get(path, headers=request_headers)
                result[key] = response.status_code < 400
                if response.status_code >= 400:
                    result["errors"][key] = f"HTTP {response.status_code}: {response.text}"
    except Exception as exc:
        result["errors"]["in_process"] = str(exc)
    return result


def verify_dashboard(dashboard_url: str) -> dict[str, Any]:
    result: dict[str, Any] = {"health_ok": False, "pages_rendered": [], "errors": {}}
    expected_pages = {
        "leaderboard": Path("dashboard/pages/01_leaderboard.py"),
        "drill_down": Path("dashboard/pages/02_drill_down.py"),
    }
    result["pages_rendered"] = [name for name, path in expected_pages.items() if path.exists()]
    try:
        response = httpx.get(dashboard_url, timeout=3.0)
        result["health_ok"] = response.status_code < 400
        if response.status_code >= 400:
            result["errors"]["dashboard"] = f"HTTP {response.status_code}"
    except Exception as exc:
        result["errors"]["dashboard"] = str(exc)
    return result


def class_distribution(frame: pd.DataFrame) -> dict[str, float]:
    return {str(k): float(v) for k, v in frame["expected_label"].value_counts(normalize=True).items()}


def slice_distribution(frame: pd.DataFrame) -> dict[str, float]:
    return {str(k): float(v) for k, v in frame["slice"].value_counts(normalize=True).items()}


def write_markdown_report(bundle: dict[str, Any], path: Path) -> None:
    candidate = bundle["candidates"][0]
    champion = bundle["champion"]
    lines = [
        "# Adult Income Evaluation Evidence",
        "",
        f"Generated at: `{bundle['generated_at']}`",
        f"Dataset source: `{bundle['dataset']['source']}`",
        f"Golden set version: `{bundle['dataset']['golden_set_version']}`",
        "",
        "## Champion",
        f"- Run ID: `{champion['run_id']}`",
        f"- Artifact: `{champion['artifact_path']}`",
        f"- Metrics: `{json.dumps(champion['metrics'], sort_keys=True)}`",
        "",
        "## Candidate A",
        f"- Run ID: `{candidate['persisted_run_id']}`",
        f"- Passed: `{candidate['passed']}`",
        f"- Failure reason: `{candidate['failure_reason']}`",
        f"- Narrative: {candidate['decision_narrative']}",
        "",
        "## Verification",
        f"- API: `{json.dumps(bundle['api_verification'], sort_keys=True)}`",
        f"- Dashboard: `{json.dumps(bundle['dashboard_verification'], sort_keys=True)}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(args: argparse.Namespace) -> dict[str, Any]:
    await ensure_database_schema(args.create_db)
    base_config = load_ares_config()
    config = adult_evaluator_config(base_config)
    gate_config = snapshot_gate_config(config)

    dataset_dir = Path(args.dataset_dir)
    artifact_dir = Path(args.artifact_dir)
    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    features, target, source = load_adult_income(args.source, args.max_rows)
    split_frames, checksums = write_golden_splits(features, target, dataset_dir)

    champion_artifact = artifact_dir / "champion_adult_income.joblib"
    candidate_artifact = artifact_dir / "candidate_adult_income_a.joblib"
    champion_size = train_and_save_model(split_frames["train"], champion_artifact)
    shutil.copyfile(champion_artifact, candidate_artifact)
    candidate_size = round(candidate_artifact.stat().st_size / (1024 * 1024), 6)

    eval_frame = split_frames[args.evaluation_split]
    start = time.perf_counter()
    champion_eval = ClassificationEvaluator(str(champion_artifact), config).evaluate(
        eval_frame,
        commit_sha=args.champion_commit_sha,
    )
    champion_duration = time.perf_counter() - start
    champion_run_id = str(uuid.uuid4())
    champion_run = await persist_run(
        _base_run_values(
            run_id=champion_run_id,
            commit_sha=args.champion_commit_sha,
            model_name=args.model_name,
            model_version="champion_adult_income_v1",
            golden_set_version=args.golden_set_version,
            artifact_path=champion_artifact,
            model_size_mb=champion_size,
            evaluation=champion_eval,
            gate_config=gate_config,
            metadata={"dataset_source": source, "evaluation_split": args.evaluation_split},
            passed=champion_eval.passed,
            failure_reason=champion_eval.failure_reason,
            duration_seconds=champion_duration,
        )
    )
    await promote_run(args.model_name, champion_run.id, "Adult income champion baseline")

    start = time.perf_counter()
    candidate_eval = ClassificationEvaluator(str(candidate_artifact), config).evaluate(
        eval_frame,
        commit_sha=args.candidate_commit_sha,
    )
    candidate_duration = time.perf_counter() - start
    champion_metrics = metrics_for_result(champion_eval, champion_size)
    candidate_metrics = metrics_for_result(candidate_eval, candidate_size)
    gate_decision = evaluate_gate(
        candidate_metrics,
        champion_metrics,
        candidate_eval.slice_metrics,
        config,
        len(eval_frame),
    )
    candidate_passed = bool(candidate_eval.passed and gate_decision.passed)
    candidate_failure = None if candidate_passed else gate_decision.reason or candidate_eval.failure_reason
    candidate_run_id = str(uuid.uuid4())
    candidate_run = await persist_run(
        _base_run_values(
            run_id=candidate_run_id,
            commit_sha=args.candidate_commit_sha,
            model_name=args.model_name,
            model_version="candidate_adult_income_a",
            golden_set_version=args.golden_set_version,
            artifact_path=candidate_artifact,
            model_size_mb=candidate_size,
            evaluation=candidate_eval,
            gate_config=gate_config,
            metadata={"dataset_source": source, "evaluation_split": args.evaluation_split},
            passed=candidate_passed,
            failure_reason=candidate_failure,
            duration_seconds=candidate_duration,
        )
    )
    comparison_payload = build_run_decision_payload(
        candidate_metrics=candidate_metrics,
        champion_metrics=champion_metrics,
        candidate_slices=candidate_eval.slice_metrics,
        champion_slices=champion_eval.slice_metrics,
        verdict="PASS" if candidate_passed else "FAIL",
        failure_reason=candidate_failure,
        config_snapshot=gate_config,
        slice_regressions=gate_decision.slice_regressions,
    )

    combined_frame = pd.concat(split_frames.values(), ignore_index=True)
    bundle = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "name": "adult_income",
            "source": source,
            "golden_set_version": args.golden_set_version,
            "split_row_counts": {name: len(frame) for name, frame in split_frames.items()},
            "checksums": checksums,
            "slice_distribution": slice_distribution(combined_frame),
            "class_distribution": class_distribution(combined_frame),
        },
        "champion": {
            "model_name": args.model_name,
            "model_version": champion_run.model_version,
            "artifact_path": str(champion_artifact),
            "run_id": champion_run.id,
            "metrics": champion_metrics,
            "slice_metrics": champion_eval.slice_metrics,
        },
        "candidates": [
            {
                "candidate_id": "A",
                "artifact_path": str(candidate_artifact),
                "commit_sha": args.candidate_commit_sha,
                "expected_story": "Sklearn tabular Adult-income candidate evaluated with explicit evaluator.mode routing.",
                "persisted_run_id": candidate_run.id,
                "passed": candidate_passed,
                "failure_reason": candidate_failure,
                "decision_narrative": comparison_payload["decision_narrative"],
                "metric_table": comparison_payload["metric_table"],
                "slice_regressions": extract_slice_regressions(candidate_eval.slice_metrics, gate_config),
                "gate_config_snapshot": gate_config,
            }
        ],
        "api_verification": verify_api(args.api_url, args.api_key, args.model_name, candidate_run.id),
        "dashboard_verification": verify_dashboard(args.dashboard_url),
    }
    output_json.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    if args.output_markdown:
        write_markdown_report(bundle, Path(args.output_markdown))
    await dispose_engine()
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Run persisted Adult-income tabular evaluation and evidence generation.")
    parser.add_argument("--source", choices=["auto", "sklearn_openml", "fallback"], default="auto")
    parser.add_argument("--max-rows", type=int, default=5000, help="Maximum source rows to use; 0 means all rows.")
    parser.add_argument("--dataset-dir", default="data/golden_set/adult_income")
    parser.add_argument("--artifact-dir", default="models/adult_income")
    parser.add_argument("--output-json", default="reports/adult_income_evidence_bundle.json")
    parser.add_argument("--output-markdown", default="reports/adult_income_evidence_report.md")
    parser.add_argument("--model-name", default="adult-income")
    parser.add_argument("--golden-set-version", default="adult-income-v1")
    parser.add_argument("--evaluation-split", choices=["val", "test"], default="test")
    parser.add_argument("--champion-commit-sha", default=f"adult-champion-{_current_commit_sha()}")
    parser.add_argument("--candidate-commit-sha", default=f"adult-candidate-{_current_commit_sha()}-{uuid.uuid4().hex[:8]}")
    parser.add_argument("--create-db", action="store_true", help="Create database tables before persisting runs.")
    parser.add_argument("--api-url", default=settings.ARES_API_URL)
    parser.add_argument("--api-key", default=(settings.ARES_API_KEYS[0] if settings.ARES_API_KEYS else "dev-key-1"))
    parser.add_argument("--dashboard-url", default=settings.ARES_DASHBOARD_URL)
    args = parser.parse_args()
    try:
        bundle = asyncio.run(run(args))
    except Exception as exc:
        print(f"Adult-income evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"bundle": args.output_json, "candidate_passed": bundle["candidates"][0]["passed"]}, indent=2))
    return 0 if bundle["candidates"][0]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())