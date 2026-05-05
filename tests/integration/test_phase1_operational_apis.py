from __future__ import annotations

import pytest

from ares.api.auth import APIKeyPrincipal, require_api_key
from ares.api.main import app

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
