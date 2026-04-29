from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from ares.config import settings


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def send_webhook(url: str, payload: dict[str, Any], secret: str | None = None) -> bool:
    if not url:
        return False
    headers = {"content-type": "application/json"}
    if secret:
        headers["x-ares-signature"] = sign_payload(payload, secret)
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
