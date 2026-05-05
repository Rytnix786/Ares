# Phase 0 Production-Grade Execution Baseline

Date: 2026-05-05 UTC
Branch: `fix/critical-and-product-completion`
Plan source: `Production_grade_final_plan.md`

## Execution model

ARES production-grade execution is being run as a coordinator-led, multi-agent program. Phase 0 used parallel read-only agents for documentation inventory, architecture inventory, and CI/testing inventory. The coordinator owns integration, verification, commits, and sequencing into Phase 1.

## Fresh verification baseline

Commands run from `H:\Projects\Ares`:

| Command | Result | Notes |
|---|---:|---|
| `python --version` | Python 3.14.0 | Local Windows environment. |
| `python -m pytest --collect-only -q -o addopts=` | 212 collected tests | Collection succeeded. |
| `python -m pytest -q -o addopts=` | Initially failed: 3 failed, 209 passed | Exposed baseline regressions in gate percentage handling and synthetic CLI smoke path. |
| Targeted regression command | 22 passed | `tests/e2e/test_full_pipeline.py::test_cli_success`, golden-set tests, and gate rules tests pass after fixes. |
| Full suite after fixes | 212 passed, 42 warnings in 12.95s | `python -m pytest -q -o addopts=` completed successfully. |

## Baseline fixes made before Phase 1

These were necessary to make the repository baseline truthful and executable before larger production work:

1. `ares/gate/rules_engine.py`
   - Added ratio normalization for config values like `10.0` meaning 10%.
   - Fixes overly permissive latency and model-size regression gates.
2. `ares/golden_set.py`
   - In checksum-skip mode, synthetic smoke datasets no longer fail production corpus row-count/class-balance/slice-distribution bounds.
   - Required columns and at-least-two-label validation still run.
3. `scripts/run_evaluation.py`
   - In checksum-skip CLI smoke mode, if the configured tabular feature set is absent from an `input`-based dataset, the CLI uses text evaluator mode for that run.
   - Avoids breaking production tabular configuration while keeping local/e2e smoke tests meaningful.

## Documentation inventory findings

Read-only docs agent findings:

- `SECURITY.md` is effectively empty and references `.github/SECURITY.md`, which is absent.
- `docs/testing-coverage-plan.md` is stale, claiming 47% coverage and 55 tests, conflicting with the current 212 collected tests and prior coverage artifacts.
- `docs/implementation-complete.md` overclaims completion despite major production gaps.
- `docs/migration-rollback.md` lists only early migrations and is stale relative to current Alembic versions.
- `docs/backup-restore.md` describes manifest-style placeholders, not production backup/restore orchestration.
- `docs/screenshots.md` and `docs/agent-workflow.md` contain patch artifacts and placeholder screenshot content.
- Missing Phase 1 docs: operator incident runbook, observability/alerting guide, SLO guide, secrets guide, deployment guide, API key lifecycle guide, dashboard operator guide, troubleshooting/tuning docs.

## Architecture inventory findings

Read-only architecture agent findings:

- `ares/api` is the FastAPI orchestration layer over DB CRUD, gate rules, presenters, auth, and rate limiting.
- `ares/models` and Alembic migrations are tightly coupled through `Base.metadata`.
- Operational scripts directly import core CRUD/session/gate/evaluator logic, so scripts should become thin wrappers around importable services before worker/API expansion.
- Dashboard is Streamlit with hardcoded `/api/v1` client paths and response-shape assumptions.
- Phase 1 risks: schema/migration drift, dashboard/API contract breakage, Alembic revision ordering, DB-specific partial indexes, global settings/session singletons, and duplicate presentation logic across scripts/API/dashboard.

## CI/testing inventory findings

Read-only CI/testing agent findings:

- `scripts/verify_repo.py` is the canonical gate and runs Ruff, Mypy, Pytest with coverage/JUnit/XML, Docker Compose config validation, DVC dry-run, and compileall.
- Workflows present: `quality.yml`, `regression_gate.yml`, `drift_monitor.yml`, `build-eval-image.yml`.
- Missing gates: compose-up service health, Docker build smoke for API/worker/dashboard, Windows matrix, package build/import smoke, security/dependency scans, enforced performance budgets, Helm validation.
- Windows blockers: Docker daemon/H-drive bind context, heavy scientific wheels/toolchain, DVC/Docker availability.

## Risk register

| Risk | Severity | Phase | Mitigation |
|---|---:|---|---|
| DB migrations for multiple Phase 1 features conflict | High | 1 | Single migration owner, model-to-migration audit, clean upgrade/downgrade tests. |
| Dashboard breaks on API response changes | High | 1-2 | Add contract tests for dashboard API client before dashboard changes. |
| Scheduler implementation conflicts with future Kubernetes CronJob | Medium | 1/3 | Introduce shared `DriftJobRunner`; scheduler frontend can be Celery/APScheduler/K8s. |
| API key lifecycle breaks env-key backward compatibility | High | 1 | Explicit backward-compat tests for env and DB keys. |
| Rollback bypasses gate/audit policy | High | 1 | Transactional rollback service, dedicated scope, rollback record, audit tests. |
| Docs overclaim production readiness | High | All | Maintain evidence index and update docs only after implementation/tests. |
| Verify script may fail locally due missing Docker/DVC | Medium | 0/All | Record partial verification and run full gate when dependencies are available. |

## Phase 1 dependency-aware task board

### Group A: schema and service foundations

1. Model/migration design for `drift_jobs`, `drift_job_runs`, production source config/batches, rollback records, API key lifecycle fields, audit query fields, alert events.
2. Add migration tests and ORM-vs-migration audit.
3. Extract importable drift/evaluation/rollback services from scripts.

### Group B: drift and alerting

1. Production data source registry and schema contracts.
2. Drift job runner with duplicate-run lock.
3. Scheduler adapter and run persistence.
4. Alert event/rule dispatch and metrics.
5. API/dashboard status after backend contracts stabilize.

### Group C: auth, audit, and errors

1. API key expiration, last-used tracking, rotation, revocation semantics.
2. Audit query API, redaction, retention policy, failure metrics.
3. Error taxonomy and stable API error response contract.
4. Security headers/CORS hardening.

### Group D: champion rollback

1. `ChampionRollback` model and transactional service.
2. Rollback API and CLI update.
3. Audit/metrics/alert integration.
4. Dashboard rollback flow after API contract tests pass.

### Group E: docs and operator workflows

1. Operator incident runbook covering drift, bad promotion, API/DB/Redis/worker failures, MLflow outage, and key compromise.
2. API key rotation guide.
3. Drift scheduler setup guide.
4. Rollback runbook.
5. Error catalog and evidence index.

## Phase 0 acceptance status

- [x] Current docs inventory complete.
- [x] Architecture and coupling risks reviewed by parallel agent.
- [x] Test collection baseline recorded: 212 tests.
- [x] Initial full-test baseline recorded and blocking regressions fixed.
- [x] Risk register created.
- [x] Phase 1 task inventory created.
- [x] Full suite after fixes recorded.
- [ ] Phase 0 artifacts committed.
