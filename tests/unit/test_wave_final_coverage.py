from __future__ import annotations

import types

import pytest

from ares.cache.client import CacheClient
from ares.db.crud_webhooks import create_webhook, list_active_webhooks
from ares.evaluators.mlflow_integration import AresMlflowLogger, categorize_mlflow_error
from ares.features.flags import is_enabled
from ares.observability import telemetry


@pytest.mark.asyncio
async def test_cache_client_text_roundtrip_and_close() -> None:
    client = CacheClient()
    await client.set("plain", "value", ttl_seconds=1)
    assert await client.get("plain") == "value"
    await client.close()


@pytest.mark.asyncio
async def test_webhook_crud(async_session) -> None:
    webhook = await create_webhook(
        async_session,
        url="https://example.test/hook",
        event_type="gate.decision",
        is_active=True,
    )
    active = await list_active_webhooks(async_session, "gate.decision")
    assert webhook in active
    assert await list_active_webhooks(async_session, "missing") == []


def test_feature_is_enabled_default() -> None:
    assert is_enabled("missing", default=True) is True


def test_more_mlflow_error_categories() -> None:
    assert categorize_mlflow_error(FileNotFoundError("not found")) == "not_found"
    assert categorize_mlflow_error(RuntimeError("boom")) == "unknown_error"


def test_mlflow_logger_noops_before_start(tmp_path) -> None:
    logger = AresMlflowLogger("experiment")
    logger.log_params({"x": "y"})
    logger.log_metrics({"metric": 1.0})
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("ok", encoding="utf-8")
    logger.log_artifact(artifact)
    logger.end_run()


def test_trace_function_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telemetry, "settings", types.SimpleNamespace(OTEL_EXPORTER_OTLP_ENDPOINT=""))

    @telemetry.trace_function("unit")
    def sample(value: int) -> int:
        return value + 1

    assert sample(1) == 2
