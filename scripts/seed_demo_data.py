#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from ares.db import crud
from ares.db.session import get_sessionmaker


def _run_payload(index: int) -> dict:
    base_time = (datetime.now(UTC) - timedelta(days=10 - index)).replace(tzinfo=None)
    passed = index not in {3, 7}
    critical_failed = index in {3, 7}
    overall_f1 = 0.91 - (0.05 if index == 3 else 0.0) - (0.03 if index == 7 else 0.0)
    overall_accuracy = 0.92 - (0.04 if index == 7 else 0.0)
    return {
        "id": f"demo-run-{index:03d}",
        "commit_sha": f"demo-commit-{index:03d}",
        "model_name": "default-model",
        "model_version": f"candidate_v{index}",
        "branch": "demo",
        "pr_number": None,
        "overall_f1": overall_f1,
        "overall_accuracy": overall_accuracy,
        "overall_precision": overall_f1,
        "overall_recall": overall_f1,
        "latency_p50_ms": 5.0 + index * 0.2,
        "latency_p99_ms": 10.0 + index * 0.4,
        "model_size_mb": 1.0 + index * 0.02,
        "slice_metrics": {
            "critical": {
                "f1": 0.55 if critical_failed else 0.88 + (index * 0.002),
                "passed_critical_threshold": not critical_failed,
                "is_critical": True,
            },
            "edge_case": {
                "f1": 0.72 - (0.06 if index == 5 else 0.0),
                "passed_critical_threshold": index != 5,
                "is_critical": True,
            },
            "typical": {
                "f1": 0.93 + (index * 0.001),
                "passed_critical_threshold": True,
                "is_critical": False,
            },
        },
        "gate_config_snapshot": {
            "max_regression_f1": 0.02,
            "max_regression_accuracy": 0.015,
            "critical_slice_min_f1": 0.60,
            "max_latency_regression_pct": 0.20,
            "significance_alpha": 0.05,
            "max_size_increase_pct": 0.15,
        },
        "metadata_json": {
            "split": "val",
            "details_url": f"http://localhost:8501/?run_id=demo-run-{index:03d}",
        },
        "passed": passed,
        "failure_reason": None if passed else "critical slice threshold failed",
        "golden_set_version": "v1.0.0",
        "n_samples_evaluated": 128,
        "duration_seconds": 1.25 + index * 0.1,
        "mlflow_run_id": None,
        "artifact_uri": None,
        "mlflow_status": "skipped",
        "mlflow_error": None,
        "created_at": base_time,
    }


async def seed_demo_runs() -> list[str]:
    seeded: list[str] = []
    async with get_sessionmaker()() as session:
        async with session.begin():
            for index in range(1, 11):
                payload = _run_payload(index)
                existing = await crud.get_evaluation_run(session, payload["id"])
                if existing is None:
                    await crud.create_evaluation_run(session, **payload)
                    seeded.append(payload["id"])

            history = await crud.list_champion_history(session, "default-model")
            active = await crud.get_active_champion(session, "default-model")
            if active is None or active.champion_run_id != "demo-run-010":
                await crud.promote_champion(
                    session,
                    "default-model",
                    "demo-run-010",
                    "seed_demo_data",
                    "Latest demo champion",
                )

            if not any(item.champion_run_id == "demo-run-006" for item in history):
                await crud.promote_champion(
                    session,
                    "default-model",
                    "demo-run-006",
                    "seed_demo_data",
                    "Historical champion #1",
                )

            active = await crud.get_active_champion(session, "default-model")
            if active is None or active.champion_run_id != "demo-run-010":
                await crud.promote_champion(
                    session,
                    "default-model",
                    "demo-run-010",
                    "seed_demo_data",
                    "Latest demo champion",
                )
    return seeded


async def seed_demo_drift() -> int:
    created = 0
    async with get_sessionmaker()() as session:
        async with session.begin():
            existing = await crud.list_drift_reports(session, model_name="default-model")
            existing_features = {report.feature for report in existing}
            for feature, psi, kl, severity in [
                ("confidence", 0.18, 0.11, "warning"),
                ("difficulty", 0.08, 0.05, "none"),
                ("response_length", 0.24, 0.17, "critical"),
            ]:
                if feature in existing_features:
                    continue
                await crud.create_drift_report(
                    session,
                    model_name="default-model",
                    feature=feature,
                    kl_divergence=kl,
                    psi=psi,
                    is_alerting=severity != "none",
                    severity=severity,
                    payload={"source": "seed_demo_data"},
                )
                created += 1
    return created


async def main() -> None:
    runs = await seed_demo_runs()
    drift_reports = await seed_demo_drift()
    print(f"Seeded demo runs: {len(runs)}")
    print(f"Seeded drift reports: {drift_reports}")


if __name__ == "__main__":
    asyncio.run(main())