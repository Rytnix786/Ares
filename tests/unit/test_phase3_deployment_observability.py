from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from ares.api.main import app
from ares.config import AresSettings
from ares.notifier.webhook import sign_payload_v1, verify_signature

ROOT = Path(__file__).resolve().parents[2]


def test_phase3_helm_and_observability_assets_are_parseable() -> None:
    chart = yaml.safe_load((ROOT / "deploy/helm/ares/Chart.yaml").read_text(encoding="utf-8"))
    values = yaml.safe_load((ROOT / "deploy/helm/ares/values.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((ROOT / "deploy/observability/prometheus-rules.yaml").read_text(encoding="utf-8"))
    dashboard = json.loads((ROOT / "deploy/observability/grafana-dashboard.json").read_text(encoding="utf-8"))

    assert chart["name"] == "ares"
    assert values["api"]["replicas"] >= 1
    assert values["api"]["autoscaling"]["enabled"] is True
    assert values["api"]["pdb"]["enabled"] is True
    assert values["containerSecurityContext"]["readOnlyRootFilesystem"] is True
    assert values["networkPolicy"]["enabled"] is True
    assert {rule["alert"] for group in rules["groups"] for rule in group["rules"]} >= {
        "AresApiHighErrorRate",
        "AresDriftAlertsFiring",
        "AresAuditWriteFailures",
    }
    assert dashboard["title"] == "ARES Production Overview"
    assert dashboard["panels"]


def test_phase3_helm_templates_cover_required_workloads() -> None:
    template_text = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "deploy/helm/ares/templates").glob("*.yaml"))

    for required in [
        "HorizontalPodAutoscaler",
        "PodDisruptionBudget",
        "ServiceAccount",
        "Ingress",
        "ServiceMonitor",
        "NetworkPolicy",
        "kind: Job",
        "range $component := list \"worker\" \"scheduler\"",
    ]:
        assert required in template_text


def test_phase3_workflows_are_parseable_and_include_expected_gates() -> None:
    workflows = {
        path.name: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in [
            ROOT / ".github/workflows/deployment.yml",
            ROOT / ".github/workflows/security.yml",
            ROOT / ".github/workflows/performance.yml",
        ]
    }

    assert "kubeconform" in json.dumps(workflows["deployment.yml"])
    assert "pip-audit" in json.dumps(workflows["security.yml"])
    assert "trivy" in json.dumps(workflows["security.yml"]).lower()
    assert "k6" in json.dumps(workflows["performance.yml"]).lower()


def test_security_headers_are_present_on_health_response() -> None:
    response = TestClient(app).get("/health/live")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_allowed_origins_parse_from_csv() -> None:
    settings = AresSettings(ARES_API_KEYS="k", ARES_ALLOWED_ORIGINS="https://ops.example.com, https://ares.example.com")

    assert settings.ARES_ALLOWED_ORIGINS == ["https://ops.example.com", "https://ares.example.com"]


def test_webhook_timestamped_signature_verifies_and_rejects_replay() -> None:
    payload = {"event": "drift", "severity": "critical"}
    timestamp, signature = sign_payload_v1(payload, "secret", timestamp=1_800_000_000)

    assert verify_signature(payload, "secret", timestamp, signature, tolerance_seconds=999_999_999)
    assert not verify_signature(payload, "secret", "1", signature, tolerance_seconds=1)
    assert not verify_signature(payload, "wrong", timestamp, signature, tolerance_seconds=999_999_999)


def test_k6_summary_validator_accepts_passing_budget(tmp_path: Path) -> None:
    summary = tmp_path / "k6-summary.json"
    summary.write_text(
        json.dumps({"metrics": {"http_req_duration": {"percentiles": {"95": 120.0}}, "http_req_failed": {"rate": 0.0}}}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/validate_k6_summary.py", str(summary)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "passed" in result.stdout
