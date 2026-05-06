from __future__ import annotations

from pathlib import Path

import pytest

from ares.api.auth import APIKeyPrincipal, require_api_key
from ares.api.main import app
from ares.db import crud
from ares.model_cards import generate_model_card
from ares.plugins import list_evaluator_plugins

HEADERS = {"X-API-Key": "test-key"}


@pytest.fixture(autouse=True)
def phase2_admin_auth_override():
    async def override_require_api_key() -> APIKeyPrincipal:
        return APIKeyPrincipal(key="phase2-test-admin", key_id="phase2-test-admin", scopes=frozenset({"read", "write", "admin"}))

    app.dependency_overrides[require_api_key] = override_require_api_key
    yield
    app.dependency_overrides.pop(require_api_key, None)


def test_builtin_evaluator_plugins_available():
    names = {plugin.name for plugin in list_evaluator_plugins()}
    assert {"classification", "regression", "detection"}.issubset(names)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_phase2_product_workflow_apis(api_client, db_session, sample_run, sample_run_2):
    await crud.persist_slice_metric_points(db_session, sample_run)
    await crud.persist_slice_metric_points(db_session, sample_run_2)
    await db_session.flush()

    evaluators = await api_client.get("/api/v1/evaluators", headers=HEADERS)
    assert evaluators.status_code == 200
    assert any(item["name"] == "classification" for item in evaluators.json())

    trends = await api_client.get(f"/api/v1/slices/trends?model_name={sample_run.model_name}&metric_name=f1", headers=HEADERS)
    assert trends.status_code == 200
    assert any(item["slice_name"] == "critical" for item in trends.json())

    threshold = await api_client.get(f"/api/v1/slices/trends?model_name={sample_run.model_name}&metric_name=f1&alert_threshold=0.95", headers=HEADERS)
    assert threshold.status_code == 200
    alerts = await api_client.get("/api/v1/alerts/events?status=open", headers=HEADERS)
    assert any(item["event_type"] == "slice_trend_threshold_breach" for item in alerts.json())

    retention = await api_client.delete("/api/v1/slices/trends/retention?retention_days=365", headers=HEADERS)
    assert retention.status_code == 200
    assert "deleted" in retention.json()

    comparison = await api_client.post("/api/v1/evaluations/compare", json={"run_ids": [sample_run.id, sample_run_2.id]}, headers=HEADERS)
    assert comparison.status_code == 200
    comparison_payload = comparison.json()
    assert comparison_payload["winner_run_id"] in {sample_run.id, sample_run_2.id}
    assert comparison_payload["winner"]["run_id"] == comparison_payload["winner_run_id"]
    assert comparison_payload["risk_summary"]["compared_candidates"] == 2
    assert [row["rank"] for row in comparison_payload["rankings"]] == [1, 2]

    card = await api_client.get(f"/api/v1/evaluations/{sample_run.id}/model-card", headers=HEADERS)
    assert card.status_code == 200
    assert "# Model Card" in card.json()["markdown"]
    assert card.json()["payload"]["run_id"] == sample_run.id
    refreshed = await crud.get_evaluation_run(db_session, sample_run.id)
    assert refreshed is not None
    assert refreshed.model_card_uri == f"ares://model-cards/{sample_run.id}.md"


def test_model_card_generator(sample_run):
    card = generate_model_card(sample_run)
    assert sample_run.id in card.markdown
    assert card.payload["model_name"] == sample_run.model_name
    normalized = card.markdown.replace(sample_run.id, "<run_id>").replace(sample_run.commit_sha, "<commit_sha>")
    expected = Path("tests/golden/model_card_default.md").read_text(encoding="utf-8")
    assert expected in normalized
