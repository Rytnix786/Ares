from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from ares.db import crud
from ares.drift.contracts import (
    ObjectPrefixDataSource,
    ingest_prediction_payload,
    load_prediction_batch,
    validate_prediction_frame,
)
from ares.drift.runner import _max_severity, run_drift_job
from ares.exceptions import DatasetSchemaError


@pytest.mark.asyncio
async def test_prediction_contract_validation_and_api_ingest(db_session):
    frame = pd.DataFrame([
        {"timestamp": "2026-05-05T00:00:00Z", "model_name": "m", "confidence": 0.5},
    ])
    assert validate_prediction_frame(frame, model_name="m").equals(frame)

    with pytest.raises(DatasetSchemaError):
        validate_prediction_frame(pd.DataFrame([{"model_name": "m"}]), model_name="m")
    with pytest.raises(DatasetSchemaError):
        validate_prediction_frame(pd.DataFrame([{"timestamp": "t", "model_name": "other", "confidence": 0.1}]), model_name="m")
    with pytest.raises(DatasetSchemaError):
        validate_prediction_frame(pd.DataFrame([{"timestamp": "t", "model_name": "m"}]), model_name="m")

    batch = await ingest_prediction_payload(db_session, model_name="m", records=frame.to_dict(orient="records"))
    assert batch.rows == 1
    assert batch.source_type == "api_push"


def test_object_prefix_and_local_source_registry(tmp_path):
    prefix = tmp_path / "predictions"
    prefix.mkdir()
    pd.DataFrame([
        {"timestamp": "t", "model_name": "m", "confidence": 0.5, "prediction": 1},
    ]).to_csv(prefix / "m_batch.csv", index=False)

    source = ObjectPrefixDataSource(str(prefix))
    assert len(source.fetch_recent_predictions("m")) == 1
    batch = load_prediction_batch("m", "object_prefix", {"prefix": str(prefix)})
    assert batch.rows == 1

    with pytest.raises(ValueError):
        load_prediction_batch("m", "unsupported", {})


@pytest.mark.asyncio
async def test_drift_runner_success_failure_and_due_job_helpers(db_session, tmp_path):
    reference = tmp_path / "reference.csv"
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    pd.DataFrame({"confidence": [0.1, 0.2, 0.3, 0.4]}).to_csv(reference, index=False)
    pd.DataFrame(
        {
            "id": ["1", "2", "3", "4"],
            "timestamp": ["t1", "t2", "t3", "t4"],
            "model_name": ["m", "m", "m", "m"],
            "prediction": [1, 1, 1, 1],
            "confidence": [0.9, 0.95, 0.97, 0.99],
        }
    ).to_csv(predictions / "m_predictions.csv", index=False)

    job = await crud.create_drift_job(
        db_session,
        model_name="m",
        job_name="hourly",
        source_type="local_file",
        source_config={"path": str(predictions)},
        reference_config={"path": str(reference)},
        thresholds={"features": ["confidence"], "psi": 0.0, "kl_divergence": 0.0, "interval_minutes": 5},
        next_run_at=datetime.utcnow() - timedelta(minutes=1),
    )
    due = await crud.list_due_drift_jobs(db_session)
    assert any(item.id == job.id for item in due)

    summary = await run_drift_job(db_session, job)
    assert summary.status == "success"
    assert summary.features_evaluated == 1
    assert summary.alerts_triggered >= 1
    assert _max_severity(["low", "high", "medium"]) == "high"

    failed = await crud.create_drift_job(
        db_session,
        model_name="missing",
        job_name="bad",
        source_type="local_file",
        source_config={"path": str(predictions)},
        reference_config={"path": str(reference)},
        thresholds={"features": ["confidence"]},
    )
    failed_summary = await run_drift_job(db_session, failed)
    assert failed_summary.status == "failed"


@pytest.mark.asyncio
async def test_alert_and_audit_crud_edges(db_session):
    assert await crud.update_alert_event_status(db_session, "missing", "resolved") is None
    old = datetime.utcnow() - timedelta(days=10)
    await crud.purge_audit_logs(db_session, older_than=old)
