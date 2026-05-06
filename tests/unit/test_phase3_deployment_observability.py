from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from ares.api.main import app
from ares.config import AresSettings

ROOT = Path(__file__).resolve().parents[2]


def test_phase3_helm_and_observability_assets_are_parseable() -> None:
    chart = yaml.safe_load((ROOT / "deploy/helm/ares/Chart.yaml").read_text(encoding="utf-8"))
    values = yaml.safe_load((ROOT / "deploy/helm/ares/values.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((ROOT / "deploy/observability/prometheus-rules.yaml").read_text(encoding="utf-8"))
    dashboard = json.loads((ROOT / "deploy/observability/grafana-dashboard.json").read_text(encoding="utf-8"))

    assert chart["name"] == "ares"
    assert values["api"]["replicas"] >= 1
    assert values["networkPolicy"]["enabled"] is True
    assert {rule["alert"] for group in rules["groups"] for rule in group["rules"]} >= {
        "AresApiHighErrorRate",
        "AresDriftAlertsFiring",
        "AresAuditWriteFailures",
    }
    assert dashboard["title"] == "ARES Production Overview"
    assert dashboard["panels"]


def test_security_headers_are_present_on_health_response() -> None:
    response = TestClient(app).get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_allowed_origins_parse_from_csv() -> None:
    settings = AresSettings(ARES_API_KEYS="k", ARES_ALLOWED_ORIGINS="https://ops.example.com, https://ares.example.com")

    assert settings.ARES_ALLOWED_ORIGINS == ["https://ops.example.com", "https://ares.example.com"]
