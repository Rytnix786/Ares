from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ares_client import AresClient, AresClientError


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            payload: Any = {"ok": True}
            if request.url.path.endswith("/runs") or request.url.path.endswith("/reports") or request.url.path.endswith("/admin/api-keys"):
                payload = []
            return httpx.Response(200, json=payload)

        return httpx.MockTransport(handler)


def make_client(recorder: Recorder) -> AresClient:
    client = AresClient("https://ares.example/api/v1", "test-key")
    client._client = httpx.Client(  # noqa: SLF001 - contract test injects transport intentionally.
        base_url=client.base_url,
        headers={"X-API-Key": "test-key"},
        transport=recorder.transport(),
    )
    return client


def assert_last(recorder: Recorder, method: str, path: str) -> httpx.Request:
    request = recorder.requests[-1]
    assert request.method == method
    assert request.url.path == path
    assert request.headers["X-API-Key"] == "test-key"
    return request


def test_phase2_contract_paths_are_declared() -> None:
    assert AresClient.contract_paths() == {
        "authenticate": ("GET", "/health/ready"),
        "submit_evaluation": ("POST", "/api/v1/evaluate/compare"),
        "compare_evaluations": ("POST", "/api/v1/evaluations/compare"),
        "get_model_card": ("GET", "/api/v1/evaluations/{run_id}/model-card"),
        "poll_job_status": ("GET", "/api/v1/drift/jobs/{job_id}/runs"),
        "get_champion": ("GET", "/api/v1/champions/{model_name}"),
        "trigger_rollback": ("POST", "/api/v1/champions/{model_name}/rollback"),
        "query_drift_reports": ("GET", "/api/v1/drift/reports"),
        "list_api_keys": ("GET", "/api/v1/admin/api-keys"),
    }


def test_client_phase2_contract_methods_send_expected_requests() -> None:
    recorder = Recorder()
    with make_client(recorder) as client:
        client.authenticate()
        assert_last(recorder, "GET", "/health/ready")

        client.submit_evaluation("fraud-v2", "abc123", {"accuracy": 0.98}, slice_metrics={"region=us": {"accuracy": 0.97}}, n_samples=500)
        request = assert_last(recorder, "POST", "/api/v1/evaluate/compare")
        assert json.loads(request.content) == {
            "model_name": "fraud-v2",
            "commit_sha": "abc123",
            "new_metrics": {"accuracy": 0.98},
            "slice_metrics": {"region=us": {"accuracy": 0.97}},
            "n_samples": 500,
        }

        client.poll_job_status("job-1")
        assert_last(recorder, "GET", "/api/v1/drift/jobs/job-1/runs")

        client.compare_evaluations(["run-a", "run-b"])
        request = assert_last(recorder, "POST", "/api/v1/evaluations/compare")
        assert json.loads(request.content) == {"run_ids": ["run-a", "run-b"]}

        client.get_model_card("run-a")
        assert_last(recorder, "GET", "/api/v1/evaluations/run-a/model-card")

        client.get_champion("fraud")
        assert_last(recorder, "GET", "/api/v1/champions/fraud")

        client.rollback_champion("fraud", reason="bad rollout", target_run_id="run-1", dry_run=True, actor="ops")
        request = assert_last(recorder, "POST", "/api/v1/champions/fraud/rollback")
        assert json.loads(request.content) == {
            "rolled_back_by": "ops",
            "reason": "bad rollout",
            "target_run_id": "run-1",
            "dry_run": True,
        }

        client.query_drift_reports("fraud")
        request = assert_last(recorder, "GET", "/api/v1/drift/reports")
        assert request.url.params["model_name"] == "fraud"

        client.list_api_keys()
        assert_last(recorder, "GET", "/api/v1/admin/api-keys")


def test_client_raises_structured_error() -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(403, json={"message": "nope"}))
    client = AresClient("https://ares.example", "bad-key")
    client._client = httpx.Client(base_url=client.base_url, transport=transport)  # noqa: SLF001
    with pytest.raises(AresClientError, match="ARES API error 403"):
        client.get_champion("fraud")
    client.close()
