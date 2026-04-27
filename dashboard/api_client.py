from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx
import streamlit as st


def get_api_base_url() -> str:
    secrets = getattr(st, "secrets", {})
    if "ARES_API_URL" in secrets:
        return str(secrets["ARES_API_URL"])
    return st.session_state.get("ARES_API_URL") or os.getenv("ARES_API_URL") or "http://localhost:8000/api/v1"


def get_api_key() -> str:
    secrets = getattr(st, "secrets", {})
    if "ARES_API_KEY" in secrets:
        return str(secrets["ARES_API_KEY"])
    return st.session_state.get("ARES_API_KEY") or os.getenv("ARES_API_KEY") or "dev-key-1"


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