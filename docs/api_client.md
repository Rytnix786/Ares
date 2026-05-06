# ARES Python API client

The `ares_client` package is included with the ARES distribution and provides a small synchronous wrapper around the production HTTP API.

## Install

```bash
pip install ares
```

## Authenticate and run the Phase 2 contract workflow

```python
from ares_client import AresClient

with AresClient("https://ares.example.com", api_key="ares_...") as client:
    # 1. Authenticate / readiness check
    ready = client.authenticate()
    assert ready["status"] == "ready"

    # 2. Submit an evaluation candidate
    evaluation = client.submit_evaluation(
        model_name="fraud-detector-v2",
        commit_sha="abc1234",
        metrics={"accuracy": 0.982, "f1": 0.941},
        slice_metrics={"country=US": {"f1": 0.936}},
        n_samples=50_000,
    )

    # 3. Poll drift job status
    runs = client.poll_job_status("drift-job-1")

    # 4. Read the current champion
    champion = client.get_champion("fraud-detector")

    # 5. Trigger a rollback if operational checks fail
    rollback = client.rollback_champion(
        "fraud-detector",
        reason="Post-promotion drift alert exceeded threshold",
        target_run_id=champion["run_id"],
        dry_run=True,
        actor="oncall",
    )

    # 6. Query drift reports
    drift_reports = client.query_drift_reports("fraud-detector")

    # 7. List API keys for admin inventory
    keys = client.list_api_keys()
```

## Contract path inventory

`AresClient.contract_paths()` returns the method/path pairs covered by client contract tests:

| Method | Client call | HTTP route |
| --- | --- | --- |
| `GET` | `authenticate()` | `/health/ready` |
| `POST` | `submit_evaluation(...)` | `/api/v1/evaluate/compare` |
| `GET` | `poll_job_status(job_id)` | `/api/v1/drift/jobs/{job_id}/runs` |
| `GET` | `get_champion(model_name)` | `/api/v1/champions/{model_name}` |
| `POST` | `rollback_champion(...)` | `/api/v1/champions/{model_name}/rollback` |
| `GET` | `query_drift_reports(...)` | `/api/v1/drift/reports` |
| `GET` | `list_api_keys()` | `/api/v1/admin/api-keys` |

The client accepts a base URL with or without `/api/v1`; versioned routes are normalized automatically while health routes remain unversioned.
