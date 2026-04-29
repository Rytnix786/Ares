import pytest
from fastapi.testclient import TestClient

from ares.api.main import app


def test_live_health():
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "alive"}


def test_openapi_loads():
    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 200


def test_request_id_header_is_returned_for_api_errors():
    client = TestClient(app)

    response = client.get("/api/v1/champions/default-model", headers={"X-API-Key": "not-valid"})

    assert response.status_code == 401
    assert response.headers["X-Request-ID"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_evaluations_returns_seeded_run(api_client, sample_run):
    response = await api_client.get("/api/v1/evaluations/", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == sample_run.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_champion_returns_schema_payload(api_client, sample_champion):
    response = await api_client.get("/api/v1/champions/default-model", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    assert response.json()["champion_run_id"] == sample_champion.champion_run_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_evaluation_detail_returns_comparison_payload(api_client, sample_champion, sample_run):
    response = await api_client.get(
        f"/api/v1/evaluations/{sample_run.id}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == sample_run.id
    assert "metric_table" in payload
    assert "decision_narrative" in payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_champion_history_returns_audit_trail(api_client, sample_champion):
    response = await api_client.get("/api/v1/champions/default-model/history", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "default-model"
    assert payload["history"][0]["champion_run_id"] == sample_champion.champion_run_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_compare_drift_and_health_routes(api_client, sample_champion, sample_run):
    export_response = await api_client.get("/api/v1/champions/export", headers={"X-API-Key": "test-key"})
    assert export_response.status_code == 200
    assert export_response.json()["champions"][0]["champion_run_id"] == sample_champion.champion_run_id

    previous_response = await api_client.get("/api/v1/champions/default-model/previous", headers={"X-API-Key": "test-key"})
    assert previous_response.status_code == 404

    compare_response = await api_client.post(
        "/api/v1/evaluate/compare",
        headers={"X-API-Key": "test-key"},
        json={
            "model_name": "default-model",
            "commit_sha": "new-commit",
            "new_metrics": {"overall_f1": 0.91, "overall_accuracy": 0.91, "latency_p99_ms": 10.0, "model_size_mb": 1.0},
            "slice_metrics": {"critical": {"f1": 0.91, "is_critical": True}},
            "n_samples": 100,
        },
    )
    assert compare_response.status_code == 200
    compare_payload = compare_response.json()
    assert compare_payload["decision"] in {"PASS", "FAIL"}
    assert compare_payload["decision_narrative"]
    assert "overall_f1" in compare_payload["metric_table"]

    drift_create = await api_client.post(
        "/api/v1/drift/reports",
        headers={"X-API-Key": "test-key"},
        json={
            "model_name": "default-model",
            "feature": "confidence",
            "kl_divergence": 0.12,
            "psi": 0.18,
            "is_alerting": True,
            "severity": "warning",
            "payload": {"source": "integration"},
        },
    )
    assert drift_create.status_code == 200

    drift_list = await api_client.get("/api/v1/drift/reports", headers={"X-API-Key": "test-key"})
    assert drift_list.status_code == 200
    assert len(drift_list.json()) >= 1

    gate_config = await api_client.get("/api/v1/gate/config", headers={"X-API-Key": "test-key"})
    assert gate_config.status_code == 200

    simulate_response = await api_client.post(
        "/api/v1/gate/simulate",
        headers={"X-API-Key": "test-key"},
        json={
            "run_id": sample_run.id,
            "override_thresholds": {"max_regression_f1": 0.01, "critical_slice_min_f1": 0.7},
        },
    )
    assert simulate_response.status_code == 200
    simulate_payload = simulate_response.json()
    assert simulate_payload["run_id"] == sample_run.id
    assert simulate_payload["decision_narrative"]
    assert "overall_f1" in simulate_payload["metric_table"]

    ready = await api_client.get("/health/ready")
    health = await api_client.get("/health")
    assert ready.status_code == 200
    assert health.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_compare_first_run_without_champion_passes(api_client):
    response = await api_client.post(
        "/api/v1/evaluate/compare",
        headers={"X-API-Key": "test-key"},
        json={
            "model_name": "brand-new-model",
            "commit_sha": "new-model-commit",
            "new_metrics": {"overall_f1": 0.8, "overall_accuracy": 0.82},
            "slice_metrics": {"typical": {"f1": 0.8, "is_critical": False}},
            "n_samples": 50,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "PASS"
    assert payload["is_first_run"] is True
    assert payload["should_promote"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_scoped_api_key_can_read_but_cannot_mutate(
    api_client,
    sample_champion,
    monkeypatch: pytest.MonkeyPatch,
):
    from ares.config import AresSettings

    monkeypatch.setattr(
        "ares.api.auth.settings",
        AresSettings(
            ENVIRONMENT="development",
            ARES_API_KEYS=["reader-key"],
            ARES_API_KEY_SCOPES={"reader-key": ["read"]},
        ),
    )

    read_response = await api_client.get(
        "/api/v1/champions/default-model",
        headers={"X-API-Key": "reader-key"},
    )
    assert read_response.status_code == 200

    promote_response = await api_client.post(
        "/api/v1/champions/default-model/promote",
        headers={"X-API-Key": "reader-key"},
        json={"run_id": sample_champion.champion_run_id, "promoted_by": "reader", "reason": "scope test"},
    )
    assert promote_response.status_code == 403
    assert promote_response.json()["detail"]["error_code"] == "INSUFFICIENT_SCOPE"