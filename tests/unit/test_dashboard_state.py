from __future__ import annotations

import json

import httpx

import dashboard.api_client as api_client
from dashboard.components.operator_state import (
    promotion_form_key,
    risk_label,
    rollback_form_key,
    rollback_payload,
)


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path.endswith("/compare"):
            return httpx.Response(200, json={"winner": {"run_id": "run-a"}, "risk_summary": {"level": "low"}})
        return httpx.Response(200, json=[] if request.url.path.endswith("/trends") else {"ok": True})


def install_mock_client(monkeypatch, recorder: Recorder) -> None:
    original_client = httpx.Client
    monkeypatch.setattr(api_client, "get_api_base_url", lambda: "https://ares.example")
    monkeypatch.setattr(api_client, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(
        api_client.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(recorder.handler), **kwargs),
    )


def test_dashboard_api_helpers_use_stable_phase2_routes(monkeypatch) -> None:
    recorder = Recorder()
    install_mock_client(monkeypatch, recorder)

    api_client.get_slice_trends("fraud", "f1")
    request = recorder.requests[-1]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/slices/trends"
    assert request.url.params["model_name"] == "fraud"
    assert request.url.params["metric_name"] == "f1"
    assert request.headers["X-API-Key"] == "test-key"

    api_client.compare_evaluation_runs(["run-a", "run-b"])
    request = recorder.requests[-1]
    assert request.method == "POST"
    assert request.url.path == "/api/v1/evaluations/compare"
    assert json.loads(request.content) == {"run_ids": ["run-a", "run-b"]}

    api_client.get_model_card("run-a")
    request = recorder.requests[-1]
    assert request.method == "GET"
    assert request.url.path == "/api/v1/evaluations/run-a/model-card"


def test_dashboard_operator_state_helpers_are_stable() -> None:
    assert promotion_form_key("run-1") == "show_promote_form_run-1"
    assert rollback_form_key("entry-1") == "show_rollback_entry-1"
    assert rollback_payload("run-0", " oncall ", " ") == {
        "target_run_id": "run-0",
        "rolled_back_by": "oncall",
        "reason": "Dashboard rollback",
        "dry_run": False,
    }
    assert risk_label(0.01) == "Low"
    assert risk_label(-0.03) == "Medium"
    assert risk_label(0.08) == "High"
