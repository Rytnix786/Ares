from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_API_ORIGIN = "http://localhost:8000"
API_V1_PREFIX = "/api/v1"

load_dotenv()


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


def get_streamlit_secret(key: str, default: Any = None) -> Any:
    try:
        return st.secrets.get(key, default)
    except StreamlitSecretNotFoundError:
        return default


def get_api_base_url() -> str:
    configured = (
        st.session_state.get("ARES_API_URL")
        or get_streamlit_secret("ARES_API_URL")
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
    configured_key = (
        st.session_state.get("ARES_API_KEY")
        or get_streamlit_secret("ARES_API_KEY")
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


def promote_champion(model_name: str, run_id: str, promoted_by: str, reason: str | None = None) -> tuple[Any | None, str | None]:
    """Promote a run to champion for the given model."""
    return safe_api_call(
        lambda client: client.post(
            api_v1_path(f"/champions/{model_name}/promote"),
            json={"run_id": run_id, "promoted_by": promoted_by, "reason": reason},
        )
    )


def rollback_champion(model_name: str, previous_run_id: str, promoted_by: str, reason: str | None = None) -> tuple[Any | None, str | None]:
    """Rollback champion by re-promoting the previous champion's run_id."""
    return safe_api_call(
        lambda client: client.post(
            api_v1_path(f"/champions/{model_name}/promote"),
            json={"run_id": previous_run_id, "promoted_by": promoted_by, "reason": f"Rollback: {reason}" if reason else "Rollback"},
        )
    )


def get_champion_history(model_name: str) -> tuple[Any | None, str | None]:
    """Get promotion history for a model."""
    return safe_api_call(
        lambda client: client.get(api_v1_path(f"/champions/{model_name}/history"))
    )


def get_champion_export() -> tuple[Any | None, str | None]:
    """Export all active champions."""
    return safe_api_call(
        lambda client: client.get(api_v1_path("/champions/export"))
    )


def get_gate_config() -> tuple[Any | None, str | None]:
    """Get current gate configuration and thresholds."""
    return safe_api_call(
        lambda client: client.get(api_v1_path("/gate/config"))
    )


def get_drift_reports(model_name: str | None = None) -> tuple[Any | None, str | None]:
    """Get drift reports, optionally filtered by model name."""
    path = api_v1_path("/drift/reports")
    if model_name:
        path = f"{path}?model_name={model_name}"
    return safe_api_call(
        lambda client: client.get(path)
    )


def create_test_drift_report(message: str) -> tuple[Any | None, str | None]:
    """Create a test drift report to verify alert channels."""
    return safe_api_call(
        lambda client: client.post(
            api_v1_path("/drift/reports"),
            json={
                "model_name": "test-model",
                "feature": "test-feature",
                "kl_divergence": 0.0,
                "psi": 0.0,
                "is_alerting": False,
                "severity": "low",
                "payload": {"test": True, "message": message},
            },
        )
    )
