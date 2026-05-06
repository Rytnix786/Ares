from __future__ import annotations

from dataclasses import dataclass

import pytest

from ares.notifier import webhook


def test_sign_payload_v1_uses_explicit_timestamp() -> None:
    timestamp, signature = webhook.sign_payload_v1({"event": "drift"}, "secret", timestamp=1710000000)

    assert timestamp == "1710000000"
    assert signature.startswith("v1=")


def test_verify_signature_respects_tolerance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webhook.time, "time", lambda: 1_000_000)
    timestamp, signature = webhook.sign_payload_v1({"event": "drift"}, "secret", timestamp=999_900)

    assert webhook.verify_signature({"event": "drift"}, "secret", timestamp, signature, tolerance_seconds=5) is False


def test_verify_signature_raises_false_for_bad_timestamp() -> None:
    assert webhook.verify_signature({"event": "drift"}, "secret", "invalid", "v1=abc") is False


@dataclass
class _QueuedResponse:
    status_code: int

    def raise_for_status(self) -> None:
        if self.status_code >= 500:
            raise RuntimeError("server error")


@pytest.mark.asyncio
async def test_send_webhook_retries_and_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            del exc_type, exc, tb

        async def post(self, url: str, *, json: dict[str, object], headers: dict[str, str]) -> _QueuedResponse:
            del url, json, headers
            attempts.append(self.timeout)
            return _QueuedResponse(status_code=500 if len(attempts) == 1 else 200)

    monkeypatch.setattr(webhook.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(webhook.settings, "WEBHOOK_MAX_RETRIES", 3)

    assert await webhook.send_webhook("https://example.test/hook", {"event": "drift"}, secret="secret") is True
    assert len(attempts) == 2