from __future__ import annotations

import pytest

from ares.notifier import webhook


def test_sign_payload_is_stable_and_order_independent() -> None:
    first = webhook.sign_payload({"b": 2, "a": 1}, "secret")
    second = webhook.sign_payload({"a": 1, "b": 2}, "secret")

    assert first == second
    assert first != webhook.sign_payload({"a": 1, "b": 3}, "secret")


@pytest.mark.asyncio
async def test_send_webhook_rejects_missing_url() -> None:
    assert await webhook.send_webhook("", {"event": "drift"}) is False


@pytest.mark.asyncio
async def test_send_webhook_posts_signed_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["raised"] = True

    class FakeClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, *, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(webhook.httpx, "AsyncClient", FakeClient)

    assert await webhook.send_webhook("https://example.test/hook", {"event": "drift"}, secret="secret") is True
    assert captured["url"] == "https://example.test/hook"
    assert captured["json"] == {"event": "drift"}
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["content-type"] == "application/json"
    assert headers["x-ares-signature"] == webhook.sign_payload({"event": "drift"}, "secret")
