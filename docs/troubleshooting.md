# Troubleshooting Guide

This guide covers the eight most common ARES failure scenarios. Each entry provides the symptom, root cause, exact diagnosis command, and exact fix command. All commands are verified against the actual codebase.

---

## 1. `scripts/verify_repo.py` exits non-zero

**Symptom**: The repository verification script fails with a non-zero exit code, blocking CI or local development.

**Root cause**: One of the six verification gates failed — Ruff lint, Mypy type check, pytest with coverage, Docker Compose config validation, DVC dry run, or compile check.

**Diagnosis**:

```bash
# Identify which gate failed by running them individually
python -m ruff check .
python -m mypy ares
python -m pytest tests/ -x --cov=ares --cov-fail-under=90
docker compose config -q
python -m dvc repro --dry
python -m compileall ares dashboard scripts tests
```

**Fix**: Address the specific failing gate. If pytest fails, run with `-x` to stop at the first failure and inspect the traceback. If Ruff fails, run `python -m ruff check . --fix` to auto-fix safe issues. If Mypy fails, add or correct type annotations. If Docker Compose fails, check `docker-compose.yml` for syntax errors. If DVC fails, verify that all pipeline stages are defined in `dvc.yaml`. Never bypass the verifier.

---

## 2. API returns 401 on every request

**Symptom**: Every API call returns `401 Unauthorized`.

**Root cause**: The `X-API-Key` header is missing, the key is not in `ARES_API_KEYS`, or the DB-managed key is inactive/expired/revoked.

**Diagnosis**:

```bash
# Confirm the header is present
curl -v http://localhost:8000/health/ready -H "X-API-Key: your-key"

# Check env keys
echo $ARES_API_KEYS

# Check DB-managed keys (requires admin scope)
curl -H "X-API-Key: $ADMIN_KEY" \
  "$ARES_API_ORIGIN/api/v1/admin/api-keys"
```

**Fix**: Add the key to `.env` as `ARES_API_KEYS=your-key` and restart the API. For DB-managed keys, create a new key via `POST /api/v1/admin/api-keys` with `write` scope, or revoke and rotate the expired one.

---

## 3. API returns 403 despite correct API key

**Symptom**: The API key is valid but every write or admin endpoint returns `403 Insufficient Scope`.

**Root cause**: The key's scopes do not include the required scope for the endpoint. Promotion, rollback, and audit endpoints require `write` or `admin`.

**Diagnosis**:

```bash
# Check the key's scopes
curl -H "X-API-Key: $ADMIN_KEY" \
  "$ARES_API_ORIGIN/api/v1/admin/api-keys"

# Inspect ARES_API_KEY_SCOPES in .env
cat .env | grep ARES_API_KEY_SCOPES
```

**Fix**: Create a new key with the correct scopes:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/admin/api-keys" \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "ops-write", "scopes": ["read", "write"]}'
```

Or update `ARES_API_KEY_SCOPES` in `.env` and restart.

---

## 4. Drift scheduler not running or producing no reports

**Symptom**: No drift reports appear for a model, or jobs exist but never produce output.

**Root cause**: No drift job is configured, the job is not scheduled, predictions have not been ingested, or the Celery worker is not running.

**Diagnosis**:

```bash
# List drift jobs
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/drift/jobs"

# List reports for a model
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/drift/reports?model_name=fraud-v2"

# Check worker status
docker compose ps worker
docker compose logs worker --tail=100
```

**Fix**: Create a drift job if none exists:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/drift/jobs" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "fraud-v2", "job_name": "daily-drift", "schedule": "0 0 * * *"}'
```

Trigger it manually:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/drift/jobs/$JOB_ID/run" \
  -H "X-API-Key: $ARES_API_KEY"
```

If `CELERY_ENABLED=true`, ensure Redis is reachable and the worker container is healthy.

---

## 5. Evaluation run stuck in PENDING state

**Symptom**: A run was submitted but never transitions from PENDING to PASS/FAIL.

**Root cause**: The evaluation worker is not running, the DB connection failed, or the run was never persisted.

**Diagnosis**:

```bash
# Check the run status
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/evaluations/$RUN_ID"

# Check worker health
docker compose ps worker
docker compose logs worker --tail=100

# Check DB connectivity from the API container
docker compose exec api python -c "import asyncio; from ares.db.session import get_db; asyncio.run(get_db())"
```

**Fix**: Restart the worker:

```bash
docker compose restart worker
```

Re-submit the evaluation if the run is missing:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/evaluate/compare" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "fraud-v2", "commit_sha": "abc123", "new_metrics": {"overall_f1": 0.91}}'
```

---

## 6. Champion promotion fails with validation error

**Symptom**: `POST /api/v1/champions/{model_name}/promote` returns `400` or `409` with a validation or promotion error.

**Root cause**: The run did not pass the gate, there is already an active champion conflict, or the API key lacks `write` scope.

**Diagnosis**:

```bash
# Confirm the run passed
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/evaluations/$RUN_ID"

# Check current champion
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME"

# Check rollback history for model conflicts
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME/rollbacks"
```

**Fix**: Ensure the run has `passed: true`. If the run failed, fix the model or data and re-evaluate. If the champion exists and you want to replace it, use the rollback endpoint first, or promote with a different target. Ensure the API key has `write` scope.

---

## 7. Rollback fails or leaves champion in inconsistent state

**Symptom**: Rollback endpoint returns an error, or the champion state does not match expectations after rollback.

**Root cause**: The target run does not belong to the same model, the run did not pass the gate, or a concurrent promotion/rollback conflicted.

**Diagnosis**:

```bash
# Run a dry-run rollback first
curl -X POST "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME/rollback" \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "investigating", "dry_run": true, "rolled_back_by": "ops"}'

# Check champion history
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME/history"

# Check rollback records
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME/rollbacks"
```

**Fix**: Ensure the target run belongs to the same model and passed the gate. If the dry run succeeds, re-run with `dry_run: false`:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/champions/$MODEL_NAME/rollback" \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "rollback due to degradation", "rolled_back_by": "ops"}'
```

If the state is inconsistent, check `champion_rollbacks` table records and contact the admin who performed the last mutation.

---

## 8. Dashboard shows "Error loading data" on every page

**Symptom**: The Streamlit dashboard displays "Error loading data" on all pages.

**Root cause**: The dashboard cannot reach the API, the API key is invalid, or CORS is blocking the cross-origin request.

**Diagnosis**:

```bash
# Check API health from the dashboard container
docker compose exec dashboard curl http://api:8000/health/ready

# Check API health from the host
curl http://localhost:8000/health/ready

# Check dashboard logs
docker compose logs dashboard --tail=100

# Verify the API key used by the dashboard
cat .env | grep ARES_API_KEY
```

**Fix**:

1. Open the dashboard sidebar and set `ARES_API_URL` to `http://localhost:8000` (or the internal Docker service name).
2. Provide a valid API key with `read` scope.
3. If running cross-origin, ensure `ARES_ALLOWED_ORIGINS` includes the dashboard origin in `.env`:

```bash
ARES_ALLOWED_ORIGINS="http://localhost:8501,http://127.0.0.1:8501"
```

4. Restart the API container to pick up the new CORS config:

```bash
docker compose restart api
```

---

## Quick-reference log commands

```bash
docker compose logs api --tail=100
docker compose logs dashboard --tail=100
docker compose logs worker --tail=100
```

Always capture the `request_id` from API error responses before escalating. The request ID correlates with structured logs and audit events.
