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
    assert "x-ares-timestamp" in headers
    assert headers["x-ares-signature"].startswith("v1=")
    assert webhook.verify_signature(
        {"event": "drift"},
        "secret",
        headers["x-ares-timestamp"],
        headers["x-ares-signature"],
    )


def test_verify_signature_rejects_bad_timestamp() -> None:
    assert webhook.verify_signature({"event": "drift"}, "secret", "not-a-number", "v1=abc") is False


@pytest.mark.asyncio
async def test_send_webhook_retries_then_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient:
        def __init__(self, *, timeout: int) -> None:
            pass

        async def __aenter__(self) -> FailingClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("connection refused")

    monkeypatch.setattr(webhook.httpx, "AsyncClient", FailingClient)
    monkeypatch.setattr(webhook.settings, "WEBHOOK_MAX_RETRIES", 3)

    result = await webhook.send_webhook("https://example.test/hook", {"event": "drift"}, secret="secret")
    assert result is False
