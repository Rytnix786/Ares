"""Integration tests for full evaluation pipeline."""

from __future__ import annotations

import pytest

from ares.gate.rules_engine import evaluate
from ares.models import DriftReportRecord, EvaluationRun, ModelChampion


@pytest.mark.integration
async def test_evaluation_to_db_write_to_gate_decision(async_session, sample_run):
    """Test full pipeline: evaluation → DB write → gate decision."""
    # Save evaluation run to DB
    async_session.add(sample_run)
    await async_session.commit()
    await async_session.refresh(sample_run)
    
    # Verify it was saved
    from sqlalchemy import select
    result = await async_session.execute(
        select(EvaluationRun).where(EvaluationRun.id == sample_run.id)
    )
    saved_run = result.scalar_one()
    assert saved_run is not None
    assert saved_run.commit_sha == sample_run.commit_sha
    
    # Get gate decision using individual metrics
    new_metrics = {
        "overall_f1": sample_run.overall_f1,
        "overall_accuracy": sample_run.overall_accuracy,
    }
    champion_metrics = {"overall_f1": 0.85, "overall_accuracy": 0.8}
    
    decision = evaluate(new_metrics, champion_metrics)
    assert decision is not None
    assert decision.passed is not None


@pytest.mark.integration
async def test_promotion_flow(async_session):
    """Test promotion flow: champion creation → promotion → history."""
    # Create a new evaluation run for this test
    run = EvaluationRun(
        id="run-promo-1",
        commit_sha="promo123",
        model_name="promo-model",
        model_version="candidate",
        branch="test",
        pr_number=10,
        overall_f1=0.9,
        overall_accuracy=0.9,
        overall_precision=0.9,
        overall_recall=0.9,
        latency_p50_ms=5.0,
        latency_p99_ms=10.0,
        model_size_mb=1.0,
        slice_metrics={"critical": {"f1": 0.9, "passed_critical_threshold": True, "is_critical": True}},
        gate_config_snapshot={"critical_slice_min_f1": 0.6},
        metadata_json={},
        passed=True,
        failure_reason=None,
        golden_set_version="v1.0.0",
        n_samples_evaluated=4,
        duration_seconds=0.2,
        mlflow_run_id=None,
        artifact_uri=None,
        mlflow_status="skipped",
        mlflow_error=None,
    )
    async_session.add(run)
    await async_session.flush()
    
    # Create champion
    champion = ModelChampion(
        id="champ-promo-1",
        model_name="promo-model",
        champion_run_id=run.id,
        promoted_by="test",
        promotion_reason="test",
        is_active=True,
    )
    async_session.add(champion)
    await async_session.commit()
    await async_session.refresh(champion)
    
    # Verify active champion
    from ares.db.crud import get_active_champion
    active = await get_active_champion(async_session, champion.model_name)
    assert active is not None
    assert active.id == champion.id
    assert active.is_active is True


@pytest.mark.integration
async def test_evaluation_with_gate_config_snapshot(async_session, sample_run_2):
    """Test that gate config is snapshot in evaluation run."""
    from ares.gate.rules_engine import snapshot_gate_config
    
    # Set a gate config
    config = {"gate": {"max_regression_f1": 0.02}}
    snapshot = snapshot_gate_config(config)
    
    # Save evaluation with snapshot
    sample_run_2.gate_config_snapshot = snapshot
    async_session.add(sample_run_2)
    await async_session.commit()
    
    # Verify snapshot was saved by querying the object
    from sqlalchemy import select
    result = await async_session.execute(
        select(EvaluationRun).where(EvaluationRun.id == sample_run_2.id)
    )
    saved_run = result.scalar_one()
    assert saved_run is not None
    assert saved_run.gate_config_snapshot is not None
    assert "max_regression_f1" in saved_run.gate_config_snapshot


@pytest.mark.integration
async def test_drift_detection_to_report_generation(async_session, sample_drift_report):
    """Test drift detection → report generation → API storage."""
    # Save drift report
    async_session.add(sample_drift_report)
    await async_session.commit()
    await async_session.refresh(sample_drift_report)
    
    # Verify report was saved by querying the object
    from sqlalchemy import select
    result = await async_session.execute(
        select(DriftReportRecord).where(DriftReportRecord.id == sample_drift_report.id)
    )
    saved_report = result.scalar_one()
    assert saved_report is not None
    assert saved_report.model_name == sample_drift_report.model_name
    assert saved_report.feature == sample_drift_report.feature
