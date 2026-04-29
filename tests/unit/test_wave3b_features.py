from __future__ import annotations

import pandas as pd
import pytest

from ares.evaluators.mlflow_integration import categorize_mlflow_error
from ares.features import FeatureFlags
from ares.golden_set import detect_outliers, freshness_status
from ares.notifier.webhook import send_webhook, sign_payload


def test_feature_flags() -> None:
    flags = FeatureFlags({"new-ui": True})
    assert flags.is_enabled("new-ui") is True
    assert flags.is_enabled("missing") is False


def test_mlflow_error_category() -> None:
    assert categorize_mlflow_error(ConnectionError("connection timeout")) == "connection_error"
    assert categorize_mlflow_error(PermissionError("forbidden")) == "auth_error"


def test_webhook_signature() -> None:
    assert sign_payload({"b": 2, "a": 1}, "secret") == sign_payload({"a": 1, "b": 2}, "secret")


@pytest.mark.asyncio
async def test_empty_webhook_url_returns_false() -> None:
    assert await send_webhook("", {"event": "x"}) is False


def test_golden_set_quality_helpers(tmp_path) -> None:
    data = pd.DataFrame({"difficulty": [1, 1, 1, 100]})
    assert detect_outliers(data, z_threshold=1.0)
    path = tmp_path / "golden.csv"
    path.write_text("id,input,expected_label,slice\n", encoding="utf-8")
    assert freshness_status(path)["status"] == "fresh"
