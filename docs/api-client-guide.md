# ARES Python API Client Guide

The local `ares_client` package provides a synchronous Python client for the main operator workflows exposed by the ARES API. It is intended for CI jobs, notebooks, release automation, and operator scripts that should not hand-roll `httpx` calls.

## Install and import

The client is packaged in this repository. From a checked-out ARES workspace, install the project in editable mode:

```bash
python -m pip install -e .
```

Then import the client:

```python
from ares_client import AresClient, AresClientError
```

## Base URL and authentication

Pass either the API origin or the `/api/v1` URL. The client normalizes both forms.

```python
with AresClient("http://localhost:8000", api_key="dev-key-1") as client:
    ready = client.authenticate()
```

Rules:

- The API key is sent as `X-API-Key`.
- API keys are never logged by the client.
- Non-2xx responses raise `AresClientError` with the status code and response body.
- The default timeout is 10 seconds. Override with `timeout=30.0` for slow local stacks.

## Core workflow example

`submit_evaluation()` calls `POST /api/v1/evaluate/compare`. It compares candidate metrics against the current champion and returns a gate decision. It does not persist a new evaluation run and therefore does not return a run ID. Use `list_evaluations()` or `get_evaluation()` for runs that already exist in the database.

```python
from ares_client import AresClient, AresClientError

metrics = {
    "overall_f1": 0.92,
    "overall_accuracy": 0.94,
    "overall_precision": 0.91,
    "overall_recall": 0.90,
    "latency_p50_ms": 42.0,
    "latency_p99_ms": 120.0,
    "model_size_mb": 18.5,
}

try:
    with AresClient("http://localhost:8000/api/v1", api_key="dev-key-1") as client:
        comparison = client.submit_evaluation(
            model_name="fraud-model",
            commit_sha="abc1234",
            metrics=metrics,
            slice_metrics={"vip_customers": {"f1": 0.88, "is_critical": True}},
            n_samples=1000,
        )
        if comparison["should_promote"]:
            print("Candidate passed comparison. Persist the run through the evaluation pipeline before promotion.")

        persisted_runs = client.list_evaluations()
        if persisted_runs:
            card = client.get_model_card(persisted_runs[0]["id"])
            print(card["markdown"])
except AresClientError as exc:
    print(f"ARES request failed: {exc}")
```

## Available methods

| Method | API path | Use case |
|---|---|---|
| `authenticate()` | `GET /health/ready` | Verify API connectivity and key validity. |
| `submit_evaluation(...)` | `POST /api/v1/evaluate/compare` | Submit candidate metrics for gate evaluation. |
| `list_evaluations()` | `GET /api/v1/evaluations/` | List persisted evaluation runs. |
| `get_evaluation(run_id)` | `GET /api/v1/evaluations/{run_id}` | Fetch one run. |
| `compare_evaluations(run_ids)` | `POST /api/v1/evaluations/compare` | Compare multiple runs for model selection. |
| `get_model_card(run_id)` | `GET /api/v1/evaluations/{run_id}/model-card` | Fetch Markdown and JSON governance evidence. |
| `list_evaluators()` | `GET /api/v1/evaluators` | Inspect built-in and plugin evaluators. |
| `slice_trends(...)` | `GET /api/v1/slices/trends` | Query normalized slice time-series points. |
| `promote_champion(...)` | `POST /api/v1/champions/{model}/promote` | Promote a passing run. |
| `get_champion(model_name)` | `GET /api/v1/champions/{model}` | Read active champion state. |
| `rollback_champion(...)` | `POST /api/v1/champions/{model}/rollback` | Run dry-run or committed governed rollback. |
| `list_drift_jobs()` | `GET /api/v1/drift/jobs` | Inspect drift schedules. |
| `poll_job_status(job_id)` | `GET /api/v1/drift/jobs/{job_id}/runs` | Inspect drift job run history. |
| `query_drift_reports(model_name=None)` | `GET /api/v1/drift/reports` | Read drift reports, optionally by model. |
| `list_api_keys()` | `GET /api/v1/admin/api-keys` | Audit managed API keys. |
| `list_alerts(status=None)` | `GET /api/v1/alerts/events` | Inspect alert lifecycle events. |

## Champion promotion and rollback

Use `promote_champion` only for runs that passed the gate. Use rollback dry-run first during incidents.

```python
with AresClient("http://localhost:8000", api_key="admin-key") as client:
    candidate = client.get_evaluation("run-123")
    if candidate["passed"]:
        client.promote_champion("fraud-model", "run-123", promoted_by="release-bot", reason="weekly release")

    preview = client.rollback_champion(
        "fraud-model",
        reason="incident INC-42 preview",
        dry_run=True,
        actor="release-bot",
    )
    print(preview)
```

## Contract coverage

`AresClient.contract_paths()` lists the API paths that contract tests lock. Update `tests/unit/test_api_client_contract.py` when adding or changing client methods so consumer/provider compatibility fails fast.

Currently contract-locked paths are: `authenticate`, `submit_evaluation`, `compare_evaluations`, `get_model_card`, `poll_job_status`, `get_champion`, `trigger_rollback`, `query_drift_reports`, and `list_api_keys`. Other methods are available client helpers but are not part of the explicit contract list yet.

## Troubleshooting

- `ARES API error 401`: check `X-API-Key`, `ARES_API_KEYS`, and managed key revocation/expiration.
- `ARES API error 403`: the key lacks required scope. Admin workflows require `admin`.
- Connection errors: verify `docker compose ps`, `http://localhost:8000/health/live`, and the base URL passed to `AresClient`.
- Empty model card or trends: ensure runs were persisted through the API/CLI paths that save gate snapshots and slice metrics.
