from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ares.db import crud
from ares.drift.contracts import load_prediction_batch_async
from ares.metrics.drift import compute_drift_report
from ares.models import DriftJob
from ares.notifier.webhook import send_webhook
from ares.observability.telemetry import trace_function


@dataclass(frozen=True)
class DriftRunSummary:
    run_id: str
    job_id: str | None
    model_name: str
    status: str
    features_evaluated: int
    alerts_triggered: int
    max_severity: str | None


def _severity_rank(severity: str) -> int:
    return {"low": 1, "medium": 2, "warning": 2, "high": 3, "critical": 4}.get(severity, 0)


def _max_severity(values: list[str]) -> str | None:
    if not values:
        return None
    return sorted(values, key=_severity_rank)[-1]


def _load_reference(reference_config: dict[str, Any]) -> pd.DataFrame:
    path = reference_config.get("path") or "data/golden_set/val.csv"
    return pd.read_csv(Path(str(path)))


def _feature_pairs(reference: pd.DataFrame, live: pd.DataFrame, features: list[str] | None) -> list[str]:
    candidates = features or [column for column in ["confidence", "prediction"] if column in live.columns and column in reference.columns]
    return [feature for feature in candidates if feature in reference.columns and feature in live.columns]


async def dispatch_drift_alerts(
    db: AsyncSession,
    *,
    report_id: str,
    run_id: str | None,
    model_name: str,
    severity: str,
    feature: str,
    payload: dict[str, Any],
    webhook_url: str | None = None,
) -> int:
    event = await crud.create_alert_event(
        db,
        event_type="drift_threshold_breach",
        source="drift_runner",
        model_name=model_name,
        severity=severity,
        status="open",
        dedupe_key=f"drift:{model_name}:{feature}:{severity}",
        drift_report_id=report_id,
        drift_run_id=run_id,
        message=f"Drift threshold breached for {model_name}.{feature}",
        payload=payload,
    )
    if webhook_url:
        await send_webhook(webhook_url, {"alert_event_id": event.id, **payload})
    return 1


@trace_function(
    "drift.run_drift_job",
    attributes={
        "drift.job_id": lambda args, kwargs: getattr(kwargs.get("job") or (args[1] if len(args) > 1 else None), "id", None),
        "drift.model_name": lambda args, kwargs: getattr(kwargs.get("job") or (args[1] if len(args) > 1 else None), "model_name", None),
        "drift.source_type": lambda args, kwargs: getattr(kwargs.get("job") or (args[1] if len(args) > 1 else None), "source_type", None),
    },
)
async def run_drift_job(
    db: AsyncSession,
    job: DriftJob,
    *,
    hours: int = 24,
    webhook_url: str | None = None,
) -> DriftRunSummary:
    start = time.perf_counter()
    started_at = datetime.utcnow()
    run = await crud.create_drift_job_run(
        db,
        job_id=job.id,
        model_name=job.model_name,
        status="running",
        started_at=started_at,
        run_metadata={"job_name": job.job_name, "source_type": job.source_type},
    )
    try:
        batch = await load_prediction_batch_async(db, job.model_name, job.source_type, job.source_config, hours=hours)
        reference = _load_reference(job.reference_config)
        features = _feature_pairs(reference, batch.data, job.thresholds.get("features"))
        alert_count = 0
        severities: list[str] = []
        for feature in features:
            report = compute_drift_report(
                feature,
                reference[feature].to_numpy(dtype=float),
                batch.data[feature].to_numpy(dtype=float),
                kl_threshold=float(job.thresholds.get("kl_divergence", job.thresholds.get("kl_threshold", 0.1))),
                psi_threshold=float(job.thresholds.get("psi", job.thresholds.get("psi_threshold", 0.2))),
            )
            record = await crud.create_drift_report(
                db,
                model_name=job.model_name,
                feature=feature,
                kl_divergence=report.kl_divergence,
                psi=report.psi,
                is_alerting=report.is_alerting,
                severity=report.severity,
                payload={"source": batch.source_type, "rows": batch.rows, "job_id": job.id},
                job_id=job.id,
                run_id=run.id,
            )
            if report.is_alerting:
                severities.append(report.severity)
                alert_count += await dispatch_drift_alerts(
                    db,
                    report_id=record.id,
                    run_id=run.id,
                    model_name=job.model_name,
                    severity=report.severity,
                    feature=feature,
                    payload={"kl_divergence": report.kl_divergence, "psi": report.psi},
                    webhook_url=webhook_url,
                )
        completed = await crud.update_drift_job_run(
            db,
            run.id,
            status="success",
            completed_at=datetime.utcnow(),
            duration_seconds=time.perf_counter() - start,
            features_evaluated=len(features),
            alerts_triggered=alert_count,
            max_severity=_max_severity(severities),
            run_metadata={"rows": batch.rows, "columns": batch.columns},
        )
        await crud.mark_drift_job_scheduled(db, job, interval_minutes=int(job.thresholds.get("interval_minutes", 60)))
        assert completed is not None
        return DriftRunSummary(completed.id, job.id, job.model_name, completed.status, completed.features_evaluated, completed.alerts_triggered, completed.max_severity)
    except Exception as exc:
        failed = await crud.update_drift_job_run(
            db,
            run.id,
            status="failed",
            completed_at=datetime.utcnow(),
            duration_seconds=time.perf_counter() - start,
            error_message=str(exc),
        )
        assert failed is not None
        return DriftRunSummary(failed.id, job.id, job.model_name, failed.status, failed.features_evaluated, failed.alerts_triggered, failed.max_severity)
