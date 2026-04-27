from __future__ import annotations

from types import SimpleNamespace

import pytest

from ares.notifier.github_pr import build_pr_comment
from ares.notifier.slack import send_slack_message
from ares.observability.telemetry import setup_telemetry
from ares.worker.tasks import evaluate_task


def test_build_pr_comment_includes_details_url() -> None:
    comment = build_pr_comment({"passed": True, "details_url": "http://example.com"})
    assert "PASSED" in comment
    assert "http://example.com" in comment


@pytest.mark.asyncio
async def test_send_slack_message_noop_without_webhook() -> None:
    await send_slack_message("", "hello")


@pytest.mark.asyncio
async def test_send_slack_message_posts_when_webhook_present(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, webhook_url: str, json: dict[str, str]):
            calls.append((webhook_url, json))
            return FakeResponse()

    monkeypatch.setattr("ares.notifier.slack.httpx.AsyncClient", lambda timeout: FakeClient())
    await send_slack_message("http://slack", "hello")
    assert calls == [("http://slack", {"text": "hello"})]


def test_setup_telemetry_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.observability.telemetry.settings", SimpleNamespace(OTEL_EXPORTER_OTLP_ENDPOINT=""))
    setup_telemetry(SimpleNamespace())


def test_evaluate_task_returns_payload() -> None:
    result = evaluate_task({"run": 1})
    assert result["status"] == "queued"
    assert result["payload"] == {"run": 1}