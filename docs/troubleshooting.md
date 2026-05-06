# Troubleshooting Guide

This guide is for operators and developers debugging ARES during local QA, CI, and production-like dry runs. Always capture the exact command, API path, request ID, and relevant logs before escalating.

## Fast health checks

```bash
docker compose ps
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8501/_stcore/health
```

Expected local state:

- API container is `healthy` and exposes port 8000.
- Dashboard container is `healthy` and exposes port 8501.
- Postgres, Redis, MinIO, and MLflow are healthy.
- Worker is running.

## API error responses

ARES structured errors include:

- `error_code`
- `message`
- `details`
- `remediation`
- `retryable`
- `request_id`
- `category`

The golden taxonomy is locked by `tests/golden/error_catalog.json` and `tests/integration/test_error_handling.py`. If a response shape changes, update the system deliberately and regenerate the snapshot with review.

### 401 invalid API key

Symptoms:

- API returns `401`.
- Dashboard shows API request failures.
- `AresClientError: ARES API error 401`.

Checks:

1. Confirm the caller sends `X-API-Key`.
2. Confirm `ARES_API_KEYS` includes the key, or a managed DB key exists and is active.
3. Check expiration and revocation for managed keys.
4. Confirm Docker containers received the intended `.env` values.

### 403 insufficient scope

Admin workflows such as promotion, rollback, and API-key management require an admin-capable key. Check `ARES_API_KEY_SCOPES`; `admin` implies all scopes.

### 429 rate limit exceeded

Slow down the caller or tune the relevant setting:

- `RATE_LIMIT_EVALUATE`
- `RATE_LIMIT_CHAMPION_MUTATION`
- `RATE_LIMIT_READ`

Do not disable rate limits in protected environments without a documented reason.

## Dashboard issues

### Dashboard cannot connect to API

1. Open the sidebar connection settings.
2. Set `ARES_API_URL` to the API origin, for example `http://localhost:8000`.
3. Provide an API key with the needed scope.
4. Confirm the API health endpoint is reachable from the dashboard container or host.

### Direct subpage load shows `_stcore` 404 console entries

Directly opening Streamlit multipage URLs such as `http://localhost:8501/leaderboard` may log 404s for `/<page>/_stcore/health` and `/<page>/_stcore/host-config`, then fall back to `/_stcore/health` and `/_stcore/host-config` successfully. This is documented Streamlit multipage behavior when a new session starts from a subpage. The supported operator path is in-app sidebar navigation, which was browser-QA verified with no console errors. See `docs/dashboard-qa-results.md`.

### Page has no data

Check the expected source:

| Page | Data source |
|---|---|
| Home and leaderboard | Evaluation runs and champion state. |
| Drill down | Selected run or details URL. |
| Drift monitor | Drift reports and slice trend points. |
| Model comparison | At least one evaluation run, ideally multiple runs. |
| Promotion workflow | Passing candidate runs and champion history. |
| Alerts | Alert events, gate config, drift reports, notification config. |

## No slice trends appear

1. Confirm evaluations include `slice_metrics`.
2. Confirm runs were persisted through `crud.create_evaluation_run` or the evaluation CLI/API path.
3. Query `/api/v1/slices/trends` with no filters first.
4. Verify `SLICE_TREND_RETENTION_DAYS` has not filtered out old points.
5. Check database migrations include the `slice_metric_points` table.

## Plugin not listed

1. Verify the package exposes an `ares.evaluators` entry point.
2. Check plugin import errors and manifest validation errors in API/worker logs.
3. Confirm the plugin is installed in the same Python environment as the API/worker.
4. Query `/api/v1/evaluators` after restart.
5. If the plugin is listed but fails when selected, verify the plugin factory returns an object compatible with `BaseEvaluator`. Return-type validation happens at evaluator creation time, not at listing time.

## Model card missing evidence

Model cards are generated from an evaluation run plus related champion, drift, and champion-history records.

Checks:

1. Confirm the evaluation run exists: `GET /api/v1/evaluations/{run_id}`.
2. Confirm metrics and `gate_config_snapshot` are present.
3. Confirm `slice_metrics` were included when the run was created.
4. Confirm drift reports exist for the model if drift evidence is expected.
5. Confirm champion history exists if promotion evidence is expected.

## Rollback does not promote previous champion

1. Run a dry run first with `scripts/rollback.py --model-name <model> --reason <reason> --dry-run`.
2. Confirm the active champion exists.
3. Confirm the previous or target run belongs to the same model and passed the gate.
4. Confirm the API key has admin scope.
5. Check `champion_rollbacks` records for status and actor evidence.

## Full verifier fails

Run the same gate locally:

```bash
python scripts/verify_repo.py
```

The verifier must pass Ruff, Mypy, pytest with coverage, Docker Compose config, DVC dry run, and compile checks. If it fails, stop feature work and fix the failing gate before continuing.

## Useful log commands

```bash
docker compose logs api --tail=100
docker compose logs dashboard --tail=100
docker compose logs worker --tail=100
```

For browser QA, use:

```bash
gstack-main/browse/dist/browse.exe status
gstack-main/browse/dist/browse.exe console --errors
gstack-main/browse/dist/browse.exe network
```
