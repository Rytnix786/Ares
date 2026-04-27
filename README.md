# Ares — Model Regression Detection System

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Coverage](https://img.shields.io/badge/coverage-90%25%2B-brightgreen)

Ares is a production-grade model regression gate for ML teams. It compares candidate models against active champions, enforces configurable regression rules, tracks evaluation history in PostgreSQL, and exposes API, dashboard, CI, DVC, and drift-monitoring workflows.

```mermaid
flowchart LR
  DVC[Golden Dataset via DVC] --> CLI[Evaluation CLI]
  CLI --> Gate[Rules Engine]
  Gate --> DB[(PostgreSQL)]
  DB --> API[FastAPI /api/v1]
  API --> Dash[Streamlit Dashboard]
  Gate --> CI[GitHub PR Gate]
  Drift[Drift Check] --> API
```

## 5-command quick start

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev,eval]"
docker compose up -d postgres redis
set DATABASE_URL=postgresql+asyncpg://ares:ares@localhost:55432/ares && alembic upgrade head && uvicorn ares.api.main:app --reload
```

## Evaluator guide

Subclass `BaseEvaluator` and implement only `load_model()`, `predict()`, and `compute_metrics()`. The base class owns dataset validation, latency measurement, slice analysis, and result assembly.

## Threshold reference

Thresholds live in `ares.config.yaml`: F1/accuracy regression tolerance, critical slice floor, latency tolerance, significance alpha, and model size increase tolerance.

## DVC workflow

`dvc.yaml` defines an `evaluate` stage. Configure a real remote before `dvc push`; placeholder `.dvcconfig` is intentionally credential-free.

## Golden dataset policy

The bundled golden set is deterministic and split into `train.csv`, `val.csv`, and `test.csv`. Use `python scripts/seed_golden_set.py` to regenerate it and `python scripts/pin_golden_checksums.py` to pin SHA-256 checksums into `ares.config.yaml`.

`run_evaluation.py` defaults to the `val` split for iterative checks. Use `--split test` only for promotion-grade evaluations.

## API versioning and migration policy

Stable endpoints are under `/api/v1`. Breaking API changes require `/api/v2`. Production code must never call `Base.metadata.create_all()`; use Alembic migrations only.

## CI/CD secrets

Configure `ARES_DB_URL`, `ARES_API_KEYS`, cloud storage credentials for DVC, and package permissions for GHCR.

## Dashboard screenshot

_Add screenshot after first local run._

## Rollback and drift runbooks

Use `scripts/rollback.py --model-name <name>` to promote the previous champion. Nightly drift runs use `.github/workflows/drift_monitor.yml` and persist JSON reports.

## Promoting a Champion

Promotion-grade checks should run against the `test` split.

### GitHub UI

1. Open **Actions** in GitHub.
2. Select **Ares Regression Gate**.
3. Choose **Run workflow**.
4. Set `split=test`.
5. Trigger the workflow for the candidate branch or commit under review.

### GitHub CLI

```bash
gh workflow run regression_gate.yml -f split=test
```

Triggering this workflow requires repository **write** access or above. In practice, maintainer approval should be required before acting on the resulting promotion signal.

If the `test` split evaluation fails, the model must not be promoted.

## Boundaries

Ares DB owns champion state and gate decisions. MLflow owns artifacts/metrics. DVC owns golden data reproducibility. Deepchecks/Evidently are optional validation/drift integrations.

## Key rotation

Set `ARES_API_KEYS` to comma-separated keys. Add the new key, migrate consumers, then remove the old key. Legacy `ARES_API_KEY` is merged deterministically.

## Champion backup/recovery

Use `GET /api/v1/champions/export` for a JSON snapshot of active champions and reconstruction references.