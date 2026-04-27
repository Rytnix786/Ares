# Ares Build Plan

## Status

This file is the working implementation plan for **Ares — Model Regression Detection System**. It is intentionally written before code implementation so the project can be refined, reviewed, and executed in a disciplined order.

Current instruction from user: execute the **v5 recovery plan** to raise the repository from scaffold-quality to a reference-grade implementation.

### Active execution checkpoint (approved v5)

The current execution order is now:

1. **C0 critical blockers**
   - asyncpg-safe integration-test DB isolation with nested transaction/savepoint pattern
   - checksum bootstrap flow with optional initial checksums and strict CI enforcement
2. **P0 foundations**
   - honest coverage + strict pytest markers + explicit mypy config
   - data contract alignment, API response schemas, rate limits, champion promotion transaction safety, valid `.dvcconfig`
3. **P1 functional completion**
   - evaluation CLI transaction integrity, checksum validation, MLflow persistence, Deepchecks summary, drift source interface, workflow split wiring, result artifact upload
4. **P2 reference-grade polish**
   - dashboard resilience, Celery feature flag gating, Makefile/pre-commit/governance/docs, compose overrides, GHCR cache, CI timeouts

Acceptance criteria for the implementation phase:

- no broad coverage omissions hiding production code
- golden dataset contains meaningful binary labels with deterministic train/val/test splits
- evaluation CLI always writes valid JSON, validates the golden set, persists evaluation history safely, and tolerates MLflow degradation without corrupt DB state
- FastAPI endpoints return schema-valid JSON and enforce configured rate limits per API key
- CI workflows preserve diagnostic artifacts and support `val` vs `test` split execution
- tests use isolated async DB sessions and the verification suite provides evidence-based completion

Milestone 0 assumptions are confirmed for execution:

- Build directly in `h:\Projects\Ares`.
- Python package path is `h:\Projects\Ares\ares`.
- Use local Docker PostgreSQL/Redis for development.
- Do not run `git commit`, `dvc push`, or real cloud credential operations without explicit approval.
- Synchronous evaluation CLI is the primary execution path.
- Celery remains optional.

---

## Project Understanding

Ares is a production-grade **Model Regression Detection System** for ML teams. It acts as a CI/CD and production monitoring layer that detects whether a candidate model regresses against the current champion model before that candidate is merged, promoted, or deployed.

Ares must provide:

- reproducible golden dataset evaluation
- champion/candidate comparison
- configurable regression gate rules
- critical slice hard-fail logic
- statistical significance checks
- evaluation history in PostgreSQL
- champion model history with rollback support
- FastAPI service under versioned routes
- Streamlit dashboard for leaderboard, drill-down, and drift monitoring
- GitHub Actions regression gate
- GHCR evaluation image workflow
- DVC-based data/versioning pipeline
- MLflow artifact/metric logging
- Evidently/Deepchecks integration points
- Slack/GitHub notifications
- Dockerized local and CI environments
- structured logs, Prometheus metrics, and optional OpenTelemetry tracing
- comprehensive unit, integration, and e2e tests

The quality target is reference-grade: the project should be strong enough to open-source as an industry reference implementation.

---

## Non-Negotiable Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Pydantic v2 |
| DB | PostgreSQL 16 / Supabase-compatible |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Data versioning | DVC 3.x with S3/GCS-compatible remote |
| Experiment tracking | MLflow 2.x |
| Dashboard | Streamlit 1.3x + Plotly |
| CI/CD | GitHub Actions |
| Containers | Docker + docker-compose |
| Tests | Pytest + pytest-asyncio + pytest-cov |
| ML validation | Deepchecks |
| Drift | Evidently AI + Ares KL/PSI metrics |
| Async jobs | Celery + Redis, optional path |
| Notifications | Slack webhooks via httpx |
| Security/config | GitHub Secrets + python-dotenv + Pydantic Settings |
| Observability | structlog, Prometheus, optional OpenTelemetry |

---

## Core Product Boundaries

### Ares DB owns

- evaluation run history
- champion model state
- champion history / soft deletes
- gate decision results
- gate config snapshots
- drift reports persisted for dashboard/API

### MLflow owns

- metric logging
- predictions CSV artifacts
- model metadata artifacts
- optional Deepchecks/Evidently artifacts

MLflow does **not** own champion state or gate decisions.

### DVC owns

- golden dataset versioning
- data pipeline reproducibility
- `dvc repro` evaluation stage

### Deepchecks owns

- optional post-evaluation validation suite
- summarized validation output stored in evaluation metadata / JSON fields

Deepchecks does **not** directly promote/fail a model unless explicitly mapped through the rules engine later.

### Evidently owns

- scheduled drift report generation
- drift artifacts from production/reference distribution comparisons

### Celery owns

- optional async evaluation jobs for API-triggered long-running work

CI must use the synchronous CLI path and must not depend on Celery.

---

## Final Implementation Policies

### 1. Database Migration Policy

- No production code may call `Base.metadata.create_all()`.
- Every schema change must go through Alembic.
- Future schema evolution must follow:
  1. add new column nullable
  2. backfill data in separate migration or script
  3. add not-null constraint only after backfill
- API container startup should run `alembic upgrade head` before starting FastAPI in local/reference deployment.
- Production Kubernetes-style deployments should run migrations as a pre-deploy job.

### 2. Evaluation Script Error Contract

`scripts/run_evaluation.py` must always write the output JSON file, even on failure.

Failure JSON shape:

```json
{
  "passed": false,
  "run_id": null,
  "details_url": null,
  "metric_table": {},
  "slice_regressions": [],
  "failure_reason": "human-readable exception message",
  "error_type": "ExceptionClassName"
}
```

The script must log the exception, write valid JSON, then exit non-zero.

### 2.1 Secrets Rotation and API Key Management

- Do **not** rely on a single static API key.
- `AresSettings` must support multi-key rotation:
  - `ARES_API_KEYS: list[str]`
  - optional backward-compatible `ARES_API_KEY` ingestion into that list
- Backward-compatibility behavior must be deterministic via a Pydantic v2 `model_validator`:
  - if `ARES_API_KEY` is set and `ARES_API_KEYS` is empty, initialize `ARES_API_KEYS` from it
  - if both are set, merge and deduplicate keys
  - if neither is set, fail config validation for protected environments
- API key validation must check against the allowed key list using constant-time comparison (`hmac.compare_digest`).
- Rotation workflow:
  1. add new key to `ARES_API_KEYS`
  2. migrate consumers gradually (CI, dashboard, scripts)
  3. remove old key after cutover

### 3. API Rate Limiting

Use `slowapi`.

Default limits:

- `/api/v1/evaluate/compare`: `10/minute` per API key
- champion mutation endpoints: `20/minute` per API key
- dashboard/read endpoints: `120/minute` per API key

Limits must be configurable in settings.

### 3.1 Database Connection Pool and Timeout Strategy

Async SQLAlchemy engine must use explicit pool settings (configurable via settings/env):

- `pool_size=10`
- `max_overflow=20`
- `pool_timeout=30`
- `pool_pre_ping=True` (mandatory)
- asyncpg `connect_args={"command_timeout": 10}`

Rationale: prevents stale connection failures after DB restarts and improves resilience under CI burst traffic.

### 4. DVC Evaluation Stage

`dvc.yaml` must define a meaningful `evaluate` stage with `cmd`, `deps`, and `outs`.

Minimum intended shape:

```yaml
stages:
  evaluate:
    cmd: >
      python scripts/run_evaluation.py
      --model-path ${MODEL_PATH}
      --commit-sha ${COMMIT_SHA}
      --model-name ${MODEL_NAME}
      --output-json reports/ares_result.json
    deps:
      - scripts/run_evaluation.py
      - data/golden_set/train.csv
      - data/golden_set/val.csv
      - ares/evaluators
      - ares/metrics
      - ares/gate
    outs:
      - reports/ares_result.json:
          cache: false
```

### 5. Dashboard URL Propagation

`AresSettings` must include `ARES_DASHBOARD_URL`.

`run_evaluation.py` builds:

```text
{ARES_DASHBOARD_URL}/drill-down?run_id={run_id}
```

This URL must appear in:

- result JSON
- GitHub PR comment
- optionally evaluation metadata

### 6. Drift Monitor Workflow

Add `scripts/run_drift_check.py` and `.github/workflows/drift_monitor.yml`.

Workflow requirements:

- cron: `0 2 * * *`
- `workflow_dispatch`
- run drift script
- upload drift report artifact
- post report to `/api/v1/drift/reports`

### 7. Liveness and Readiness

Implement:

- `GET /health/live` → no I/O, returns `{"status": "alive"}`
- `GET /health/ready` → DB ping, returns readiness status
- `GET /health` → compatibility summary

Docker healthcheck must use `/health/live`.

### 7.1 Champion State Backup and Disaster Recovery

- Since Ares DB is source-of-truth for champion state, champion data must be exportable.
- Add endpoint: `GET /api/v1/champions/export`.
- Endpoint returns JSON snapshot containing active champions and linked evaluation references needed for reconstruction.
- Supabase automatic backups are primary recovery path; export endpoint is secondary rapid-recovery mechanism.

### 8. Optional OpenTelemetry

Add optional observability dependencies and `setup_telemetry()`.

Telemetry must no-op unless `OTEL_EXPORTER_OTLP_ENDPOINT` is configured.

### 9. Docker Hardening

Every Dockerfile must:

- create non-root user `ares`
- own app directory with that user
- switch to `USER ares` before runtime
- avoid running application as root

### 10. Versioning Policy

API:

- stable routes live under `/api/v1`
- breaking changes require a new `/api/v2` router
- previous major version remains supported for one major release cycle

Golden dataset:

- `ares.config.yaml` includes `data.golden_set_version`
- settings include `GOLDEN_SET_VERSION`
- any golden set change increments this version
- version should correspond to git tag/commit over DVC metadata
- idempotency key includes golden set version, so changing data invalidates old cache entries

### 11. Evaluation Data Retention and Storage Policy

- PostgreSQL should store aggregated metrics and decision metadata, not large raw prediction blobs.
- `raw_predictions` should be stored as artifacts (MLflow/artifact store), not persisted in DB JSON columns.
- `EvaluationRun` should include references such as:
  - `mlflow_run_id`
  - `artifact_uri`
- Dashboard/API drill-down should fetch summary metrics from DB and link to artifacts for deep inspection.

### 12. Concurrent Champion Promotion Safety

- Champion promotion must be concurrency-safe for simultaneous CI runs.
- `promote_champion` must use transactional locking, preferably:
  - `SELECT ... FOR UPDATE` on current active champion row for target model
  - then deactivate old and activate new within one transaction
- Alternative (if needed): optimistic locking with `updated_at`/version checks.
- Partial unique active index remains required as the final integrity guard.

---

## Required Repository Structure

The implementation should create the structure specified in `ARES_AGENT_INSTRUCTIONS.md`, with these additional files included:

```text
.github/workflows/build-eval-image.yml
scripts/run_drift_check.py
docker/entrypoint.api.sh
reports/.gitkeep
plan.md
```

---

## Execution Roadmap

### Milestone 0 — Confirm assumptions

- Build directly in `h:\Projects\Ares`.
- Python package path: `h:\Projects\Ares\ares`.
- Use local Docker PostgreSQL/Redis for development.
- Do not run `git commit`, `dvc push`, or real cloud credential operations without approval.
- Synchronous evaluation CLI is primary.
- Celery is optional.

### Milestone 1 — Scaffold and foundation

Create:

- exact directory structure
- `pyproject.toml`
- `.gitignore`
- `.env.example`
- `ares/config.py`
- `ares.config.yaml`
- logging setup
- telemetry setup

`pyproject.toml` test configuration must enforce coverage as a hard gate (not advisory), e.g.:

```toml
[tool.pytest.ini_options]
addopts = "--cov=ares --cov-fail-under=90"
```

`.gitignore` must include runtime artifacts:

- `reports/*.json`

Important: use `reports/*.json` (not `reports/`) so `reports/.gitkeep` remains committed and the directory exists in fresh clones.

### Milestone 2 — Data contract and DVC foundation

Create:

- `data/schemas/data_contract.json`
- `.dvcconfig`
- `.dvcignore`
- `dvc.yaml`
- `reports/.gitkeep`
- `scripts/seed_golden_set.py`

### Milestone 3 — DB models and Alembic

Create:

- SQLAlchemy models
- Alembic async environment
- initial migration
- migration policy docs

Important constraints:

- unique idempotency key: `commit_sha + golden_set_version + model_name`
- partial unique active champion index: `model_name WHERE is_active = true`
- `EvaluationRun.gate_config_snapshot` JSON column
- `EvaluationRun` stores artifact references (`mlflow_run_id`, `artifact_uri`) instead of large `raw_predictions` payloads

### Milestone 4 — DB session and CRUD

Create:

- async engine/session dependency
- CRUD functions for evaluation runs, champions, cached lookups, drift reports
- champion export function for recovery snapshot
- promotion transaction must apply row-level lock (`SELECT FOR UPDATE`) or equivalent optimistic lock guard

### Milestone 5 — Metrics and gate

Create:

- significance utilities
- slice analysis
- drift metrics
- decision dataclasses
- rules engine
- gate config snapshot helper

### Milestone 6 — Evaluators

Create:

- `BaseEvaluator.evaluate()` as canonical orchestrator
- classification evaluator
- regression evaluator
- detection evaluator scaffold

Concrete evaluators only override:

- `load_model()`
- `predict()`
- `compute_metrics()`

Dataset convention for `BaseEvaluator.evaluate(dataset: pd.DataFrame)` is mandatory:

- required columns: `id`, `input`, `expected_label`, `slice`
- optional column: `difficulty`
- `input` can be any model-consumable object (commonly dict-like)
- `evaluate()` must validate required columns up front and raise clear `ValueError` if missing

### Milestone 7 — Synchronous evaluation CLI

Create `scripts/run_evaluation.py`.

Must:

- work without Celery
- always write result JSON
- use corrected idempotency key
- snapshot gate config
- log MLflow metrics/artifacts
- optionally run Deepchecks
- compute `details_url`

### Milestone 8 — FastAPI API

Create:

- schemas
- routers
- auth dependency
- rate limiting
- Prometheus metrics
- optional OTEL setup

Auth dependency must:

- validate incoming API key against `ARES_API_KEYS`
- use constant-time comparisons (`hmac.compare_digest`)

Required endpoints:

- `GET /health/live`
- `GET /health/ready`
- `GET /health`
- `GET /metrics`
- `POST /api/v1/evaluate/compare`
- `GET /api/v1/evaluations/`
- `GET /api/v1/evaluations/{run_id}`
- `GET /api/v1/champions/export`  
  *(static routes must be registered before parameterized champion routes to avoid routing conflicts)*
- `GET /api/v1/champions/{model_name}`
- `POST /api/v1/champions/{model_name}/promote`
- `GET /api/v1/champions/{model_name}/previous`
- `GET /api/v1/gate/config`
- `POST /api/v1/drift/reports`
- `GET /api/v1/drift/reports`

### Milestone 9 — Optional Celery worker

Create:

- Celery config
- worker task wrapping evaluation
- eager-mode tests

### Milestone 10 — Notifications, rollback, drift check

Create:

- Slack notifier
- GitHub helper if useful
- `scripts/rollback.py`
- `scripts/run_drift_check.py`

### Milestone 11 — Docker

Create:

- `docker/Dockerfile.api`
- `docker/Dockerfile.worker`
- `docker/Dockerfile.eval`
- `docker/entrypoint.api.sh`
- `docker-compose.yml`
- `docker-compose.ci.yml`

All runtime containers must use non-root `ares` user.

### Milestone 12 — GitHub Actions

Create:

- `.github/workflows/build-eval-image.yml`
- `.github/workflows/regression_gate.yml`
- `.github/workflows/drift_monitor.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`

### Milestone 13 — Dashboard

Create:

- `dashboard/app.py`
- `dashboard/pages/01_leaderboard.py`
- `dashboard/pages/02_drill_down.py`
- `dashboard/pages/03_drift_monitor.py`
- `dashboard/components/charts.py`
- dashboard API client with `st.secrets` / env fallback

### Milestone 14 — Tests

Create `tests/conftest.py` with:

- async DB session fixture
- migration/setup fixture
- sample evaluation run factory
- sample champion factory
- dummy evaluator fixture
- sample dataset fixture
- config override fixture

Test categories:

- unit tests for metrics/gate/evaluators
- integration tests for API/DB
- rate limit tests
- CLI failure JSON tests
- e2e full pipeline test

### Milestone 15 — README and docs

README must include:

- badges
- Mermaid architecture diagram
- 5-command quick start
- evaluator guide
- threshold reference
- DVC workflow
- golden set versioning policy
- API versioning policy
- migration policy
- CI/CD secrets and workflow guide
- dashboard screenshot placeholder
- rollback/drift runbooks
- system boundary definitions

Also include:

- release/versioning policy (SemVer + API/versioning behavior)
- key rotation operational guide
- backup/recovery notes for champion state export

Create additional open-source readiness docs:

- `CHANGELOG.md` (Keep a Changelog format, pre-populated for v1.0.0)
- `CONTRIBUTING.md` covering evaluator extension workflow, gate rule extension, local test/lint/type commands, PR checklist
- `LICENSE` (recommended: MIT or Apache-2.0)

### Milestone 16 — Verification

Run where possible:

```bash
ruff check .
mypy ares
pytest --cov=ares --cov-report=term-missing
docker compose config
dvc repro --dry
```

Also perform:

- API health smoke test
- Streamlit import smoke test
- security review
- migration safety review
- CI/CD viability review

---

## Skill / Tool Mapping

| Area | Best skill/tool | Purpose |
|---|---|---|
| Architecture | `senior-architect`, `software-architecture` | System boundaries and sequencing |
| Python | `python-patterns`, `clean-code` | Typed maintainable Python |
| API | `api-and-interface-design`, `api-security-best-practices` | Versioned secure FastAPI |
| DB | `database-design`, `deprecation-and-migration` | Schema, indexes, migrations |
| Tests | `test-driven-development`, `testing-patterns`, `test-fixing` | Correctness and coverage |
| Docker | `docker-expert`, `security-and-hardening` | Secure containers |
| CI/CD | `ci-cd-and-automation`, `github-workflow-automation` | Workflows and GHCR |
| Dashboard | `ui-ux-pro-max`, `frontend-ui-engineering` | Polished Streamlit UX |
| Observability | `performance-optimization`, `backend-dev-guidelines` | Logs, metrics, tracing |
| Verification | `verification-before-completion`, `code-review-and-quality` | Final evidence and review |

---

## Risks / Open Questions

1. Real DVC remote is unknown.
   - Use placeholder config and docs until credentials are provided.

2. Production prediction source for drift is unknown.
   - Implement adapter/interface plus local/sample source.

3. GHCR package permissions may require repo settings.
   - Workflow can be correct, but repo must allow package writes.

4. API startup migrations are acceptable for docker-compose/reference deployment but should be a pre-deploy job in production.

5. Deepchecks/Evidently may be heavy.
   - Keep optional and isolated from core gate path.

6. Exact DVC stage syntax may need validation once DVC is installed.

---

## Immediate Next Step

Proceed to Milestone 1: scaffold the repository foundation.
