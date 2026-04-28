from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import httpx
import streamlit as st

DEFAULT_API_ORIGIN = "http://localhost:8000"
API_V1_PREFIX = "/api/v1"


def _first_configured_api_key(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return next((str(item).strip() for item in parsed if str(item).strip()), None)
    return next((item.strip() for item in value.split(",") if item.strip()), None)


def _strip_api_v1_suffix(value: str) -> str:
    normalized = value.rstrip("/")
    if normalized.endswith(API_V1_PREFIX):
        return normalized[: -len(API_V1_PREFIX)]
    return normalized


def get_api_base_url() -> str:
    secrets = getattr(st, "secrets", {})
    configured = (
        st.session_state.get("ARES_API_URL")
        or secrets.get("ARES_API_URL")
        or os.getenv("ARES_API_URL")
        or DEFAULT_API_ORIGIN
    )
    return _strip_api_v1_suffix(str(configured))


def api_v1_path(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized.startswith(API_V1_PREFIX):
        return normalized
    return f"{API_V1_PREFIX}{normalized}"


def get_api_key() -> str:
    secrets = getattr(st, "secrets", {})
    configured_key = (
        st.session_state.get("ARES_API_KEY")
        or secrets.get("ARES_API_KEY")
        or os.getenv("ARES_API_KEY")
        or _first_configured_api_key(os.getenv("ARES_API_KEYS"))
    )
    return configured_key or "dev-key-1"


def create_client() -> httpx.Client:
    return httpx.Client(
        base_url=get_api_base_url(),
        headers={"X-API-Key": get_api_key()},
        timeout=10.0,
    )


def safe_api_call(request_fn: Callable[[httpx.Client], Any]) -> tuple[Any | None, str | None]:
    try:
        with create_client() as client:
            response = request_fn(client)
            response.raise_for_status()
            return response.json(), None
    except httpx.HTTPStatusError as exc:
        return None, f"API request failed: {exc.response.status_code} {exc.response.text}"
    except httpx.HTTPError as exc:
        return None, f"Unable to connect to Ares API: {exc}"