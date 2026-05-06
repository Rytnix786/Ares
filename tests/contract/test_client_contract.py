from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from ares.api.main import app
from ares_client.client import AresClient


@dataclass(frozen=True)
class ClientMethodCase:
    method_name: str
    http_method: str
    openapi_path: str
    invoke: Any


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            payload: Any = {"ok": True}
            if request.method == "GET" and request.url.path.endswith("/evaluations/"):
                payload = []
            elif request.method == "GET" and request.url.path.endswith("/evaluators"):
                payload = []
            elif request.method == "GET" and request.url.path.endswith("/trends"):
                payload = []
            elif request.method == "GET" and request.url.path.endswith("/jobs"):
                payload = []
            elif request.method == "GET" and request.url.path.endswith("/reports"):
                payload = []
            elif request.method == "GET" and request.url.path.endswith("/events"):
                payload = []
            elif request.url.path.endswith("/admin/api-keys"):
                payload = []
            elif request.url.path.endswith("/runs"):
                payload = []
            return httpx.Response(200, json=payload)

        return httpx.MockTransport(handler)


def _make_client(recorder: Recorder) -> AresClient:
    client = AresClient("https://ares.example/api/v1", "test-key")
    client._client = httpx.Client(  # noqa: SLF001
        base_url=client.base_url,
        headers={"X-API-Key": "test-key"},
        transport=recorder.transport(),
    )
    return client


def _load_openapi_schema() -> dict[str, Any]:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    return dict(response.json())


def _template_for_request_path(
    openapi_schema: dict[str, Any],
    actual_path: str,
    http_method: str,
) -> str | None:
    for candidate_path, operations in openapi_schema.get("paths", {}).items():
        if not isinstance(operations, dict) or http_method.lower() not in operations:
            continue
        actual_parts = actual_path.strip("/").split("/")
        candidate_parts = candidate_path.strip("/").split("/")
        if len(actual_parts) != len(candidate_parts):
            continue
        matches = True
        for actual_part, candidate_part in zip(actual_parts, candidate_parts, strict=True):
            if candidate_part.startswith("{") and candidate_part.endswith("}"):
                continue
            if actual_part != candidate_part:
                matches = False
                break
        if matches:
            return candidate_path
    return None


CLIENT_CASES = [
    ClientMethodCase("authenticate", "GET", "/health/ready", lambda client: client.authenticate()),
    ClientMethodCase(
        "submit_evaluation",
        "POST",
        "/api/v1/evaluate/compare",
        lambda client: client.submit_evaluation(
            "fraud-v2",
            "abc123",
            {"overall_f1": 0.98, "overall_accuracy": 0.97},
            slice_metrics={"critical": {"f1": 0.96, "is_critical": True}},
            n_samples=300,
        ),
    ),
    ClientMethodCase(
        "poll_job_status",
        "GET",
        "/api/v1/drift/jobs/{job_id}/runs",
        lambda client: client.poll_job_status("job-1"),
    ),
    ClientMethodCase(
        "list_evaluations",
        "GET",
        "/api/v1/evaluations/",
        lambda client: client.list_evaluations(),
    ),
    ClientMethodCase(
        "get_evaluation",
        "GET",
        "/api/v1/evaluations/{run_id}",
        lambda client: client.get_evaluation("run-1"),
    ),
    ClientMethodCase(
        "compare_evaluations",
        "POST",
        "/api/v1/evaluations/compare",
        lambda client: client.compare_evaluations(["run-a", "run-b"]),
    ),
    ClientMethodCase(
        "get_model_card",
        "GET",
        "/api/v1/evaluations/{run_id}/model-card",
        lambda client: client.get_model_card("run-a"),
    ),
    ClientMethodCase(
        "list_evaluators",
        "GET",
        "/api/v1/evaluators",
        lambda client: client.list_evaluators(),
    ),
    ClientMethodCase(
        "slice_trends",
        "GET",
        "/api/v1/slices/trends",
        lambda client: client.slice_trends(model_name="fraud-v2", metric_name="overall_f1"),
    ),
    ClientMethodCase(
        "promote_champion",
        "POST",
        "/api/v1/champions/{model_name}/promote",
        lambda client: client.promote_champion(
            "fraud-v2",
            "run-123",
            promoted_by="client",
            reason="candidate promoted",
        ),
    ),
    ClientMethodCase(
        "get_champion",
        "GET",
        "/api/v1/champions/{model_name}",
        lambda client: client.get_champion("fraud-v2"),
    ),
    ClientMethodCase(
        "rollback_champion",
        "POST",
        "/api/v1/champions/{model_name}/rollback",
        lambda client: client.rollback_champion(
            "fraud-v2",
            reason="rollback requested",
            target_run_id="run-122",
            dry_run=True,
            actor="ops",
        ),
    ),
    ClientMethodCase(
        "list_drift_jobs",
        "GET",
        "/api/v1/drift/jobs",
        lambda client: client.list_drift_jobs(),
    ),
    ClientMethodCase(
        "query_drift_reports",
        "GET",
        "/api/v1/drift/reports",
        lambda client: client.query_drift_reports("fraud-v2"),
    ),
    ClientMethodCase(
        "list_api_keys",
        "GET",
        "/api/v1/admin/api-keys",
        lambda client: client.list_api_keys(),
    ),
    ClientMethodCase(
        "list_alerts",
        "GET",
        "/api/v1/alerts/events",
        lambda client: client.list_alerts("open"),
    ),
    ClientMethodCase(
        "optimize_thresholds",
        "POST",
        "/api/v1/gate/optimize",
        lambda client: client.optimize_thresholds(
            [
                {
                    "candidate_metrics": {"overall_f1": 0.91, "overall_accuracy": 0.90},
                    "champion_metrics": {"overall_f1": 0.90, "overall_accuracy": 0.89},
                }
            ]
        ),
    ),
]


def test_every_public_http_method_is_covered_by_contract_cases() -> None:
    public_methods = {
        name
        for name, member in inspect.getmembers(AresClient, predicate=inspect.isfunction)
        if not name.startswith("_") and name not in {"close", "contract_paths"}
    }
    covered_methods = {case.method_name for case in CLIENT_CASES}
    assert public_methods == covered_methods


@pytest.mark.parametrize(
    ("method_name", "http_method", "openapi_path", "invoke"),
    [
        (case.method_name, case.http_method, case.openapi_path, case.invoke)
        for case in CLIENT_CASES
    ],
)
def test_client_method_matches_openapi_contract(
    method_name: str,
    http_method: str,
    openapi_path: str,
    invoke: Any,
) -> None:
    openapi_schema = _load_openapi_schema()
    assert openapi_path in openapi_schema["paths"]
    assert http_method.lower() in openapi_schema["paths"][openapi_path]

    recorder = Recorder()
    with _make_client(recorder) as client:
        invoke(client)

    request = recorder.requests[-1]
    assert request.method == http_method
    assert request.headers["X-API-Key"] == "test-key"
    assert (
        _template_for_request_path(openapi_schema, request.url.path, request.method) == openapi_path
    ), f"{method_name} called {request.method} {request.url.path}, expected {openapi_path}"

    if method_name == "compare_evaluations":
        assert json.loads(request.content) == {"run_ids": ["run-a", "run-b"]}
    if method_name == "list_alerts":
        assert request.url.params["status"] == "open"
