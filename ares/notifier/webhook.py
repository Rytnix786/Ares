from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import httpx

from ares.config import settings


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def sign_payload_v1(payload: dict[str, Any], secret: str, timestamp: int | None = None) -> tuple[str, str]:
    ts = str(timestamp or int(time.time()))
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hmac.new(secret.encode("utf-8"), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return ts, f"v1={digest}"


def verify_signature(
    payload: dict[str, Any],
    secret: str,
    timestamp: str,
    signature: str,
    tolerance_seconds: int = 300,
) -> bool:
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > tolerance_seconds:
        return False
    _ts, expected = sign_payload_v1(payload, secret, ts)
    return hmac.compare_digest(signature, expected)


async def send_webhook(url: str, payload: dict[str, Any], secret: str | None = None) -> bool:
    if not url:
        return False
    headers = {"content-type": "application/json"}
    if secret:
        timestamp, signature = sign_payload_v1(payload, secret)
        headers["x-ares-timestamp"] = timestamp
        headers["x-ares-signature"] = signature
    last_error: Exception | None = None
    for _attempt in range(max(settings.WEBHOOK_MAX_RETRIES, 1)):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return True
        except Exception as exc:  # pragma: no cover - exercised with mocked clients
            last_error = exc
    if last_error:
        return False
    return False
