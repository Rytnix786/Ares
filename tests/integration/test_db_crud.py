from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ares.db import crud
from ares.exceptions import PromotionError


@pytest.mark.integration
@pytest.mark.asyncio
async def test_crud_round_trip(db_session, sample_run):
    fetched = await crud.get_evaluation_run(db_session, sample_run.id)
    assert fetched is not None
    assert fetched.id == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_promote_and_export_champion(db_session, sample_run):
    champion = await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester", "integration")
    assert champion.is_active is True
    exported = await crud.export_champions(db_session)
    assert exported["champions"][0]["champion_run_id"] == sample_run.id
    history = await crud.list_champion_history(db_session, sample_run.model_name)
    assert history[0].champion_run_id == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rollback_champion_dry_run_and_commit(db_session, sample_run, sample_run_2):
    first = await crud.promote_champion(
        db_session,
        sample_run.model_name,
        sample_run.id,
        "tester",
        "initial promotion",
    )
    second = await crud.promote_champion(
        db_session,
        sample_run.model_name,
        sample_run_2.id,
        "tester",
        "second promotion",
    )

    dry_run = await crud.rollback_champion(
        db_session,
        sample_run.model_name,
        rolled_back_by="operator",
        reason="incident validation",
        dry_run=True,
    )

    assert dry_run["dry_run"] is True
    assert dry_run["from_champion"].id == second.id
    assert dry_run["to_run_id"] == first.champion_run_id

    committed = await crud.rollback_champion(
        db_session,
        sample_run.model_name,
        rolled_back_by="operator",
        reason="bad promotion",
    )

    active = await crud.get_active_champion(db_session, sample_run.model_name)
    assert active is not None
    assert active.champion_run_id == sample_run.id
    assert committed["champion"].action == "rollback"
    assert committed["champion"].rolled_back_from_id == second.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rollback_champion_validates_reason_and_target(db_session, sample_run, sample_run_2):
    await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester")

    with pytest.raises(PromotionError, match="rollback reason is required"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason=" ",
        )

    with pytest.raises(PromotionError, match="target evaluation run not found"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="missing target",
            target_run_id="missing-run",
        )

    with pytest.raises(PromotionError, match="target run belongs to a different model"):
        sample_run_2.model_name = "other-model"
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="wrong model",
            target_run_id=sample_run_2.id,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_and_list_drift_report(db_session):
    report = await crud.create_drift_report(
        db_session,
        model_name="default-model",
        feature="confidence",
        kl_divergence=0.2,
        psi=0.3,
        is_alerting=True,
        severity="warning",
        payload={"source": "test"},
    )
    reports = await crud.list_drift_reports(db_session, model_name="default-model")
    assert reports[0].id == report.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_evaluation_run_persists_points_and_supports_cached_lookup(db_session, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class _Span:
        def set_attribute(self, key: str, value: object) -> None:
            captured[key] = value

    monkeypatch.setattr("opentelemetry.trace.get_current_span", lambda: _Span())

    run = await crud.create_evaluation_run(
        db_session,
        id="created-run",
        commit_sha="cache-me",
        model_name="cached-model",
        model_version="candidate",
        branch="test",
        pr_number=7,
        overall_f1=0.92,
        overall_accuracy=0.91,
        overall_precision=0.93,
        overall_recall=0.90,
        latency_p50_ms=4.0,
        latency_p99_ms=9.0,
        model_size_mb=1.2,
        slice_metrics={
            "critical": {
                "f1": 0.88,
                "latency": 12.0,
                "is_critical": True,
                "passed_critical_threshold": True,
            }
        },
        gate_config_snapshot={"critical_slice_min_f1": 0.7},
        metadata_json={},
        passed=True,
        failure_reason=None,
        golden_set_version="v1",
        n_samples_evaluated=16,
        duration_seconds=0.6,
        mlflow_run_id=None,
        artifact_uri=None,
        mlflow_status="skipped",
        mlflow_error=None,
    )

    cached = await crud.get_cached_evaluation(db_session, "cache-me", "v1", "cached-model")
    points = await crud.list_slice_metric_trends(db_session, model_name="cached-model", slice_name="critical", metric_name="f1")

    assert run.id == "created-run"
    assert cached is not None and cached.id == run.id
    assert [point.metric_name for point in points] == ["f1"]
    assert points[0].metric_value == pytest.approx(0.88)
    assert captured["model_name"] == "cached-model"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_champion_and_latest_prediction_batch_filters(db_session, sample_run):
    champion = await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester", "baseline")
    await crud.create_prediction_batch(
        db_session,
        model_name="batched-model",
        source="api_push",
        rows=2,
        columns=["timestamp", "model_name", "confidence"],
        records=[{"timestamp": "2026-05-05T00:00:00Z", "model_name": "batched-model", "confidence": 0.8}],
    )
    await crud.create_prediction_batch(
        db_session,
        model_name="batched-model",
        source="http_push",
        rows=1,
        columns=["timestamp", "model_name", "confidence"],
        records=[{"timestamp": "2026-05-05T00:01:00Z", "model_name": "batched-model", "confidence": 0.9}],
    )

    latest_any = await crud.latest_prediction_batch(db_session, "batched-model")
    latest_http = await crud.latest_prediction_batch(db_session, "batched-model", source="http_push")

    assert (await crud.get_champion(db_session, sample_run.model_name)).id == champion.id
    assert latest_any is not None and latest_any.model_name == "batched-model"
    assert latest_http is not None and latest_http.source == "http_push"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_promote_and_rollback_wrap_unexpected_errors(db_session, sample_run, monkeypatch: pytest.MonkeyPatch):
    async def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("db exploded")

    monkeypatch.setattr(db_session, "execute", boom)

    with pytest.raises(PromotionError, match="db exploded"):
        await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester")

    with pytest.raises(PromotionError, match="db exploded"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="incident",
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rollback_champion_additional_validation_paths(db_session, sample_run, sample_run_2):
    await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester")

    with pytest.raises(PromotionError, match="no previous champion available"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="no previous",
        )

    sample_run_2.passed = False
    with pytest.raises(PromotionError, match="target run did not pass the gate"):
        await crud.rollback_champion(
            db_session,
            sample_run.model_name,
            rolled_back_by="operator",
            reason="bad target",
            target_run_id=sample_run_2.id,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_drift_job_helpers_attach_model_card_and_update_run(db_session, sample_run):
    job_active = await crud.create_drift_job(
        db_session,
        id="job-active",
        model_name="default-model",
        job_name="active",
        status="active",
        next_run_at=datetime.utcnow() - timedelta(minutes=5),
        source_type="local_file",
        source_config={"path": "data/sample_predictions"},
        reference_config={},
        thresholds={},
    )
    await crud.create_drift_job(
        db_session,
        id="job-inactive",
        model_name="other-model",
        job_name="inactive",
        status="inactive",
        next_run_at=datetime.utcnow() - timedelta(minutes=5),
        source_type="local_file",
        source_config={"path": "data/sample_predictions"},
        reference_config={},
        thresholds={},
    )
    run = await crud.create_drift_job_run(
        db_session,
        id="run-1",
        job_id=job_active.id,
        model_name="default-model",
        status="running",
        run_metadata={"state": "started"},
    )
    await crud.create_alert_event(
        db_session,
        id="event-open",
        event_type="drift",
        source="test",
        model_name="default-model",
        severity="high",
        status="open",
        message="open",
        payload={},
    )
    resolved = await crud.create_alert_event(
        db_session,
        id="event-resolved",
        event_type="drift",
        source="test",
        model_name="default-model",
        severity="high",
        status="open",
        message="to resolve",
        payload={},
    )
    await crud.create_audit_log(
        db_session,
        request_id="audit-1",
        user="operator",
        endpoint="/api/v1/drift/jobs",
        method="POST",
        payload_hash="hash",
        result="success",
        status_code=200,
        audit_metadata={},
        action="create",
        resource_type="drift_job",
        resource_id=job_active.id,
    )

    assert await crud.attach_model_card(db_session, "missing-run", markdown_uri="uri", payload={}) is None
    attached = await crud.attach_model_card(db_session, sample_run.id, markdown_uri="uri://card", payload={"ok": True})
    assert attached is not None and attached.model_card_uri == "uri://card"

    assert await crud.update_drift_job_run(db_session, "missing-run", status="failed") is None
    updated_run = await crud.update_drift_job_run(db_session, run.id, status="completed", error_message="none")
    assert updated_run is not None and updated_run.status == "completed"

    assert await crud.get_drift_job(db_session, job_active.id) is not None
    filtered_jobs = await crud.list_drift_jobs(db_session, model_name="default-model", status="active")
    filtered_runs = await crud.list_drift_job_runs(db_session, job_id=job_active.id, model_name="default-model")
    due_jobs = await crud.list_due_drift_jobs(db_session, now=datetime.utcnow())

    assert [job.id for job in filtered_jobs] == [job_active.id]
    assert [job.id for job in due_jobs] == [job_active.id]
    assert [item.id for item in filtered_runs] == [run.id]

    await crud.mark_drift_job_scheduled(db_session, job_active, interval_minutes=30)
    assert job_active.last_run_at is not None
    assert job_active.next_run_at is not None

    open_events = await crud.list_alert_events(db_session, model_name="default-model", status="open")
    resolved_event = await crud.update_alert_event_status(db_session, resolved.id, "resolved", actor="ops")
    assert resolved_event is not None and resolved_event.resolved_by == "ops"
    assert any(event.id == "event-open" for event in open_events)

    filtered_audit_logs = await crud.list_audit_logs(db_session, action="create", resource_type="drift_job")
    assert [entry.request_id for entry in filtered_audit_logs] == ["audit-1"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_drift_reports_and_update_evaluation_run_trace(db_session, sample_run, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, object] = {}

    class _Span:
        def set_attribute(self, key: str, value: object) -> None:
            captured[key] = value

    monkeypatch.setattr("opentelemetry.trace.get_current_span", lambda: _Span())

    await crud.create_drift_report(
        db_session,
        model_name=sample_run.model_name,
        feature="confidence",
        kl_divergence=0.1,
        psi=0.2,
        is_alerting=False,
        severity="low",
        payload={},
    )

    reports = await crud.get_drift_reports(db_session, model_name=sample_run.model_name, limit=5)
    assert reports and reports[0].feature == "confidence"

    assert await crud.update_evaluation_run(db_session, "missing-run", passed=False) is None
    updated = await crud.update_evaluation_run(db_session, sample_run.id, passed=False, failure_reason="regressed")

    assert updated is not None
    assert updated.passed is False
    assert updated.failure_reason == "regressed"
    assert captured["model_name"] == sample_run.model_name
