from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request

from ares.api.auth import APIKeyPrincipal, require_api_key
from ares.api.main import app
from ares.api.routers import drift as drift_router
from ares.api.schemas.drift import DriftPredictionIngestRequest
from ares.models import DriftJob, DriftJobRun

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture(autouse=True)
def phase1_admin_auth_override():
    async def override_require_api_key() -> APIKeyPrincipal:
        return APIKeyPrincipal(
            key="phase1-test-admin",
            key_id="phase1-test-admin",
            scopes=frozenset({"read", "write", "admin"}),
        )

    app.dependency_overrides[require_api_key] = override_require_api_key
    yield
    app.dependency_overrides.pop(require_api_key, None)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_drift_prediction_ingest_and_job_api(api_client, tmp_path):
    records = [
        {"timestamp": "2026-05-05T00:00:00Z", "model_name": "default-model", "confidence": 0.9},
        {"timestamp": "2026-05-05T00:01:00Z", "model_name": "default-model", "confidence": 0.8},
    ]
    ingest = await api_client.post("/api/v1/drift/predictions", json={"model_name": "default-model", "records": records}, headers=HEADERS)
    assert ingest.status_code == 200
    assert ingest.json()["rows"] == 2

    job_payload = {
        "model_name": "default-model",
        "job_name": "hourly-confidence",
        "source_type": "local_file",
        "source_config": {"path": "data/sample_predictions"},
        "reference_config": {"path": "data/golden_set/val.csv"},
        "thresholds": {"features": ["confidence"], "psi": 0.0, "kl_divergence": 0.0},
        "created_by": "test",
    }
    created = await api_client.post("/api/v1/drift/jobs", json=job_payload, headers=HEADERS)
    assert created.status_code == 200
    job = created.json()
    assert job["job_name"] == "hourly-confidence"

    listed = await api_client.get("/api/v1/drift/jobs", headers=HEADERS)
    assert listed.status_code == 200
    assert any(item["id"] == job["id"] for item in listed.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_alert_event_lifecycle_api(api_client, db_session):
    from ares.db import crud

    event = await crud.create_alert_event(
        db_session,
        event_type="drift_threshold_breach",
        source="test",
        model_name="default-model",
        severity="high",
        status="open",
        message="test alert",
        payload={"psi": 1.0},
    )
    await db_session.flush()

    listed = await api_client.get("/api/v1/alerts/events?status=open", headers=HEADERS)
    assert listed.status_code == 200
    assert any(item["id"] == event.id for item in listed.json())

    updated = await api_client.patch(f"/api/v1/alerts/events/{event.id}", json={"status": "acknowledged", "actor": "tester"}, headers=HEADERS)
    assert updated.status_code == 200
    assert updated.json()["status"] == "acknowledged"
    assert updated.json()["acknowledged_by"] == "tester"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_api_key_lifecycle_api(api_client):
    created = await api_client.post(
        "/api/v1/admin/api-keys",
        json={"name": "phase1-test", "key": "phase1-secret", "scopes": ["read"], "ttl_days": 7},
        headers=HEADERS,
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["key"] == "phase1-secret"
    key_id = payload["record"]["id"]

    listed = await api_client.get("/api/v1/admin/api-keys", headers=HEADERS)
    assert listed.status_code == 200
    assert any(item["id"] == key_id for item in listed.json())

    rotated = await api_client.post(f"/api/v1/admin/api-keys/{key_id}/rotate", json={"key": "phase1-secret-2", "grace_days": 1}, headers=HEADERS)
    assert rotated.status_code == 200
    assert rotated.json()["record"]["rotated_from_key_id"] == key_id

    revoked = await api_client.post(f"/api/v1/admin/api-keys/{rotated.json()['record']['id']}/revoke", json={"revoked_by": "tester", "reason": "done"}, headers=HEADERS)
    assert revoked.status_code == 200
    assert revoked.json() == {"revoked": True}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_query_and_retention_api(api_client, db_session):
    from ares.models import AuditLog

    db_session.add(AuditLog(
        request_id="req-phase1",
        user="tester",
        endpoint="/api/v1/champions/default-model/rollback",
        method="POST",
        payload_hash="abc123",
        result="success",
        status_code=200,
        audit_metadata={"action": "rollback"},
    ))
    await db_session.flush()

    listed = await api_client.get("/api/v1/audit/events?user=tester", headers=HEADERS)
    assert listed.status_code == 200
    assert any(item["request_id"] == "req-phase1" for item in listed.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_governed_rollback_api(api_client, db_session, sample_run, sample_run_2):
    from ares.db import crud

    first = await crud.promote_champion(db_session, sample_run.model_name, sample_run.id, "tester")
    second = await crud.promote_champion(db_session, sample_run.model_name, sample_run_2.id, "tester")

    dry_run = await api_client.post(
        f"/api/v1/champions/{sample_run.model_name}/rollback",
        json={"rolled_back_by": "operator", "reason": "incident", "dry_run": True},
        headers=HEADERS,
    )
    assert dry_run.status_code == 200
    assert dry_run.json()["from_champion_id"] == second.id
    assert dry_run.json()["to_run_id"] == first.champion_run_id
    assert dry_run.json()["dry_run"] is True

    committed = await api_client.post(
        f"/api/v1/champions/{sample_run.model_name}/rollback",
        json={"rolled_back_by": "operator", "reason": "incident"},
        headers=HEADERS,
    )
    assert committed.status_code == 200
    assert committed.json()["champion"]["champion_run_id"] == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_drift_push_ingest_and_run_listing_routes(db_session, monkeypatch: pytest.MonkeyPatch):
    records = [
        {"timestamp": "2026-05-05T00:00:00Z", "model_name": "push-model", "confidence": 0.4},
    ]
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/drift/predictions/push", "headers": [], "query_string": b""})
    pushed = await drift_router.ingest_predictions_push(
        request,
        DriftPredictionIngestRequest(model_name="push-model", records=records),
        db_session,
        object(),
    )
    assert pushed.source == "http_push"
    assert pushed.rows == 1

    job = DriftJob(
        id="drift-job-1",
        model_name="push-model",
        job_name="manual",
        source_type="http_push",
        source_config={"source": "http_push"},
        reference_config={},
        thresholds={},
        status="active",
    )
    db_session.add(job)
    db_session.add(
        DriftJobRun(
            id="drift-run-1",
            job_id=job.id,
            model_name="push-model",
            status="success",
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=1.5,
            features_evaluated=2,
            alerts_triggered=0,
            max_severity="low",
            run_metadata={"source": "test"},
        )
    )
    await db_session.flush()

    async def fake_run_drift_job(db, found_job):  # type: ignore[no-untyped-def]
        del db
        assert found_job.id == job.id
        return SimpleNamespace(job_id=job.id)

    async def fake_list_drift_job_runs(db, job_id=None, limit=1, model_name=None):  # type: ignore[no-untyped-def]
        del db, limit, model_name
        assert job_id == job.id
        return [
                DriftJobRun(
                    id="drift-run-now",
                    job_id=job.id,
                    model_name="push-model",
                    status="success",
                    created_at=datetime.utcnow(),
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow(),
                duration_seconds=0.5,
                features_evaluated=1,
                alerts_triggered=0,
                max_severity="low",
                run_metadata={"trigger": "manual"},
            )
        ]

    listed = await drift_router.list_job_runs(request, job.id, 100, db_session, object())
    assert listed[0].id == "drift-run-1"
    assert listed[0].run_metadata["source"] == "test"

    monkeypatch.setattr("ares.api.routers.drift.run_drift_job", fake_run_drift_job)
    monkeypatch.setattr("ares.api.routers.drift.crud.list_drift_job_runs", fake_list_drift_job_runs)

    ran = await drift_router.run_job_now(request, job.id, db_session, object())
    assert ran.id == "drift-run-now"
    assert ran.run_metadata["trigger"] == "manual"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_drift_router_not_found_and_validation_failures(db_session):
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/drift/jobs/missing-job/run", "headers": [], "query_string": b""})

    with pytest.raises(HTTPException) as exc_info:
        await drift_router.run_job_now(request, "missing-job", db_session, object())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Drift job not found"

    with pytest.raises(ValueError, match="List should have at least 1 item"):
        DriftPredictionIngestRequest(model_name="push-model", records=[])
