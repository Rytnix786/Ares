<div align="center">
# ⚔️ ARES

Decide whether a candidate ML model is safe to promote before it reaches production.

![Build](https://img.shields.io/github/actions/workflow/status/Rytnix786/Ares/quality.yml?branch=main&label=quality&style=flat-square)
![Regression Gate](https://img.shields.io/github/actions/workflow/status/Rytnix786/Ares/regression_gate.yml?branch=main&label=regression%20gate&style=flat-square)
![Version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)
![License](https://img.shields.io/github/license/Rytnix786/Ares?style=flat-square)
![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)
![Language](https://img.shields.io/github/languages/top/Rytnix786/Ares?style=flat-square)

[Demo](#demo) · [Quickstart](#quickstart) · [Docs](#usage) · [Contributing](#contributing)

</div>

---

## Overview

ARES is a Python 3.11+ model regression detection system for ML teams that need evidence before replacing a production champion model. It evaluates a candidate against a golden dataset, compares it with the active champion, applies configurable gate rules, records the decision trail, and exposes the result through a FastAPI API, CLI workflow, Streamlit dashboard, DVC stage, and GitHub Actions gates.

The differentiator is the promotion workflow: ARES does not only compute metrics. It stores champion history, checks critical slices, snapshots gate configuration, keeps idempotent evaluation records, emits decision narratives, and supports drift reports for ongoing model monitoring.

## ✨ Features

- 🏆 Candidate-vs-champion comparison with pass/fail promotion decisions.
- 🧪 Golden-set validation with checksum, row-count, class-balance, and slice-distribution checks.
- 🧩 Classification, regression, and detection evaluator surfaces built around `BaseEvaluator`.
- 🚦 Configurable regression gates for F1, accuracy, critical slices, latency, model size, and statistical significance.
- 📊 Streamlit operator dashboard with leaderboard, drill-down, drift monitor, model comparison, promotion workflow, and alert configuration pages.
- 🔁 Idempotent evaluation persistence keyed by `commit_sha`, `golden_set_version`, and `model_name`.
- 🗄️ Async SQLAlchemy models and Alembic migrations for evaluation runs, champions, drift reports, API keys, webhooks, and audit logs.
- 🔐 API-key authentication with environment-backed keys, DB-backed hashed keys, scopes, and rate limits.
- 📈 Prometheus instrumentation at `/metrics`, structured logging, request IDs, and optional OpenTelemetry export.
- 🧰 Docker Compose stack for PostgreSQL, Redis, MinIO, MLflow, API, worker, and dashboard services.
- 🤖 GitHub Actions workflows for quality checks, regression gating, drift monitoring, and eval-image publishing.

## Demo

![ARES dashboard placeholder](docs/assets/screenshots/hero-placeholder.png)

The repository currently includes placeholder screenshot assets under `docs/assets/screenshots/`. The capture plan for real dashboard, CLI, and API screenshots is documented in [`docs/screenshots.md`](docs/screenshots.md).

## Architecture

See the Phase 4 architecture explorer in [`docs/architecture/README.md`](docs/architecture/README.md) for the current module graph, Graphify artifact locations, and reading order.

```mermaid
flowchart TD
    GH[GitHub Actions<br/>quality.yml / regression_gate.yml / drift_monitor.yml] --> CLI[scripts/run_evaluation.py]
    DVC[dvc.yaml<br/>evaluate stage] --> CLI
    DATA[data/golden_set<br/>train / val / test / slices] --> VALIDATE[ares.golden_set<br/>validation + checksums]
    VALIDATE --> EVAL[ares.evaluators<br/>BaseEvaluator + concrete evaluators]
    MODEL[models/<br/>candidate / champion artifacts] --> EVAL
    CONFIG[ares.config.yaml<br/>gate + drift + evaluator config] --> EVAL
    CONFIG --> GATE[ares.gate<br/>rules_engine + decision narratives]
    EVAL --> GATE
    GATE --> DB[(PostgreSQL / SQLite<br/>SQLAlchemy models)]
    DB --> API[FastAPI<br/>ares.api.main]
    API --> DASH[Streamlit dashboard<br/>leaderboard / drill-down / drift / promotion]
    API --> PROM[Prometheus /metrics<br/>request IDs / telemetry]
    API --> NOTIFY[Slack / GitHub / webhooks]
    DRIFT[scripts/run_drift_check.py<br/>KL + PSI reports] --> DB
    WORKER[Celery worker<br/>ares.worker.tasks] --> DB
```

## Quickstart

```bash
git clone https://github.com/Rytnix786/Ares.git
cd Ares
cp .env.example .env
python -m venv .venv && . .venv/bin/activate && python -m pip install -e ".[dev,eval,dashboard]"
docker compose up -d && python -m alembic upgrade head && python scripts/seed_champion.py && make verify
```

Windows `cmd.exe` equivalent:

```cmd
git clone https://github.com/Rytnix786/Ares.git
cd Ares
copy .env.example .env
python -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev,eval,dashboard]"
docker compose up -d && python -m alembic upgrade head && python scripts\seed_champion.py && make.cmd verify
```

Local surfaces after startup:

| Surface | URL |
|---|---|
| FastAPI API | `http://localhost:8000` |
| OpenAPI docs | `http://localhost:8000/docs` |
| Streamlit dashboard | `http://localhost:8501` |
| MLflow | `http://localhost:5000` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |

## Installation

### Prerequisites

| Dependency | Version / source | Used for |
|---|---|---|
| Python | `>=3.11` | ARES package, API, CLI, dashboard, tests |
| Docker + Docker Compose | current Docker CLI | Local PostgreSQL, Redis, MinIO, MLflow, API, worker, dashboard |
| Git | any supported version | Clone, CI metadata, Docker images |
| Make or `make.cmd` | GNU Make or bundled Windows script | Project command shortcuts |

### Install

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,eval,dashboard,otel]"
pre-commit install
```

### Verify

```bash
python scripts/verify_repo.py
```

`verify_repo.py` runs Ruff, Mypy, Pytest with `--cov-fail-under=90`, Docker Compose config validation, `dvc repro --dry`, and `compileall` over `ares`, `dashboard`, `scripts`, and `tests`.

## Usage

### Run the full local stack

```bash
docker compose up -d
python -m alembic upgrade head
python scripts/seed_champion.py
python scripts/seed_demo_data.py
streamlit run dashboard/app.py
```

The API container also runs migrations at startup through `docker/entrypoint.api.sh`.

### Evaluate a candidate model

```bash
python scripts/run_evaluation.py \
  --model-path models/candidate.json \
  --commit-sha local \
  --model-name default-model \
  --model-version candidate \
  --split val \
  --output-json reports/ares_result.json
```

Run against the held-out test split for promotion-grade evidence:

```bash
python scripts/run_evaluation.py \
  --model-path models/candidate.json \
  --commit-sha "$(git rev-parse --short HEAD)" \
  --model-name default-model \
  --split test \
  --run-deepchecks \
  --output-json reports/ares_result.json
```

### Add a custom evaluator

```python
from typing import Any

from ares.evaluators.base import BaseEvaluator


class MyEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self._model = {"default_label": "positive"}

    def predict(self, inputs: list[Any]) -> list[Any]:
        return [self._model["default_label"] for _ in inputs]

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        correct = sum(str(pred) == str(label) for pred, label in zip(predictions, ground_truth, strict=False))
        accuracy = correct / max(len(ground_truth), 1)
        return {
            "overall_accuracy": accuracy,
            "overall_f1": accuracy,
            "overall_precision": accuracy,
            "overall_recall": accuracy,
            "f1": accuracy,
        }
```

### Compare metrics through the API

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/compare \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-1" \
  -d '{
    "model_name": "default-model",
    "commit_sha": "local",
    "new_metrics": {
      "overall_f1": 0.91,
      "overall_accuracy": 0.92,
      "overall_precision": 0.90,
      "overall_recall": 0.93,
      "latency_p99_ms": 10.0,
      "model_size_mb": 1.0
    },
    "slice_metrics": {
      "critical": {"f1": 0.88, "is_critical": true},
      "typical": {"f1": 0.93, "is_critical": false}
    },
    "n_samples": 128
  }'
```

### Run drift detection

```bash
python scripts/run_drift_check.py
curl -X POST http://localhost:8000/api/v1/drift/reports \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-1" \
  --data @reports/drift_report.json
```

### Manage API keys

```bash
python scripts/manage_api_keys.py create --name local-operator --scopes read,write
python scripts/manage_api_keys.py list
python scripts/manage_api_keys.py revoke <key_id>
```

### Backup, restore validation, and rollback

```bash
python scripts/backup.py --output reports/ares-backup.json
python scripts/restore.py reports/ares-backup.json
python scripts/rollback.py --model-name default-model --reason "failed production monitor"
```

## Configuration

Environment variables are loaded by `ares.config.AresSettings` from `.env`, with Compose overrides for container-to-container URLs.

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment; `production` and `staging` require API keys. |
| `DATABASE_URL` | `postgresql+asyncpg://ares:ares@localhost:55432/ares` | Async SQLAlchemy database URL. |
| `DB_POOL_SIZE` | `10` | SQLAlchemy async pool size for non-SQLite databases. |
| `DB_MAX_OVERFLOW` | `20` | Extra DB connections above the pool size. |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a DB connection. |
| `DB_COMMAND_TIMEOUT` | `10` | Async PostgreSQL command timeout. |
| `ARES_API_KEY` | `None` | Legacy single API key merged into `ARES_API_KEYS`. |
| `ARES_API_KEYS` | `[]` | Comma-separated or JSON-array API keys. |
| `ARES_API_KEY_SCOPES` | `{}` | JSON map of key to scopes; missing keys default to `read`, `write`, `admin`. |
| `ARES_API_URL` | `http://localhost:8000/api/v1` | API base URL used by scripts and dashboard. |
| `ARES_DASHBOARD_URL` | `http://localhost:8501` | Dashboard URL used in details links. |
| `CELERY_ENABLED` | `false` | Feature flag for async worker usage. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker, cache, and Celery backend URL. |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow tracking server URL. |
| `MLFLOW_EXPERIMENT` | `ares-evaluations` | MLflow experiment name. |
| `AWS_ACCESS_KEY_ID` | empty | S3/MinIO access key. |
| `AWS_SECRET_ACCESS_KEY` | empty | S3/MinIO secret key. |
| `AWS_REGION` | `us-east-1` | S3-compatible region. |
| `AWS_ENDPOINT_URL` | empty | S3-compatible endpoint; Compose points this at MinIO. |
| `DVC_REMOTE_URL` | `s3://ares-data` | DVC remote path. |
| `RATE_LIMIT_EVALUATE` | `10/minute` | SlowAPI limit for evaluation endpoints. |
| `RATE_LIMIT_CHAMPION_MUTATION` | `20/minute` | SlowAPI limit for champion and drift mutations. |
| `RATE_LIMIT_READ` | `120/minute` | SlowAPI limit for read endpoints. |
| `CACHE_ENABLED` | `true` | Toggle Redis cache client behavior. |
| `CACHE_TTL_SECONDS` | `300` | Default cache TTL. |
| `CACHE_KEY_PREFIX` | `ares` | Prefix for generated cache keys. |
| `CACHE_CONNECT_TIMEOUT_SECONDS` | `2.0` | Redis connection timeout. |
| `CACHE_SOCKET_TIMEOUT_SECONDS` | `2.0` | Redis socket timeout. |
| `API_KEY_HASH_SECRET` | `secret` | HMAC secret for DB-backed API-key hashes. |
| `API_KEY_DEFAULT_RATE_LIMIT` | `120/minute` | Default rate limit recorded for DB API keys. |
| `API_KEY_HASH_PREFIX_LENGTH` | `64` | Stored API-key hash prefix length. |
| `GOLDEN_SET_VERSION` | `v1.0.0` | Version recorded on evaluation runs. |
| `GOLDEN_SET_REQUIRE_CHECKSUM` | `false` | Require configured golden-set checksum matches. |
| `GOLDEN_SET_SKIP_CHECKSUM` | `false` | Skip golden-set checksum validation. |
| `SLACK_WEBHOOK_URL` | empty | Slack notification webhook. |
| `GITHUB_TOKEN` | empty | GitHub notification token. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty | Enables OpenTelemetry export when set. |
| `ARES_FEATURE_FLAGS` | `{}` | JSON feature-flag map consumed by `ares.features.flags`. |
| `WEBHOOK_MAX_RETRIES` | `3` | Retry count for webhook dispatch. |
| `MINIO_ENDPOINT` | unset | Optional readiness-check endpoint for MinIO. |
| `MINIO_ACCESS_KEY` | unset | Optional readiness-check access key for MinIO. |
| `MINIO_SECRET_KEY` | unset | Optional readiness-check secret key for MinIO. |
| `DATA_PATH` | `.` | Disk path checked by `/health/ready`. |
| `ALERT_EMAIL` | unset | Dashboard alert-channel setting read from Streamlit secrets/env. |

Gate and evaluator settings live in `ares.config.yaml`.

| Key | Default in repo | Description |
|---|---:|---|
| `data.golden_set_version` | `adult-real-v1` | Golden-set version described by config checksums and bounds. |
| `data.checksums.train` | configured SHA-256 | Expected `train.csv` checksum. |
| `data.checksums.val` | configured SHA-256 | Expected `val.csv` checksum. |
| `data.checksums.test` | configured SHA-256 | Expected `test.csv` checksum. |
| `data.row_count_bounds.*` | configured min/max | Allowed row-count ranges per split. |
| `data.class_balance_bounds.*` | configured min/max | Allowed positive/negative class-balance ranges. |
| `data.slice_distribution_bounds.*` | configured min/max | Allowed slice-distribution ranges. |
| `gate.max_regression_f1` | `0.02` | Maximum allowed absolute F1 drop. |
| `gate.max_regression_accuracy` | `0.015` | Maximum allowed absolute accuracy drop. |
| `gate.critical_slice_min_f1` | `0.6` | Minimum F1 required for critical slices. |
| `gate.max_latency_regression_pct` | `10.0` | Maximum p99 latency regression ratio used by current config. |
| `gate.significance_alpha` | `0.05` | Alpha for one-sided significance checks. |
| `gate.max_size_increase_pct` | `10.0` | Maximum model-size increase ratio used by current config. |
| `drift.kl_divergence_alert_threshold` | `0.1` | KL divergence alert threshold. |
| `drift.psi_alert_threshold` | `0.2` | Population Stability Index alert threshold. |
| `drift.production_error_spike_pct` | `0.1` | Production error spike threshold. |
| `drift.local_predictions_dir` | `data/sample_predictions` | Local prediction source for drift checks. |
| `evaluator.mode` | `sklearn_tabular` | Classification evaluator mode. |
| `evaluator.feature_columns` | Adult-income feature list | Feature order for tabular sklearn models. |
| `evaluator.positive_label` | `positive` | Label mapping for positive class. |
| `evaluator.negative_label` | `negative` | Label mapping for negative class. |

## API / CLI Reference

### HTTP API

All application endpoints use `X-API-Key` unless the API is running in development with no keys configured.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health/live` | Liveness probe. |
| `GET` | `/health/ready` | Readiness probe for DB, Redis, MinIO, and disk space. |
| `GET` | `/health` | Health probe with DB connectivity and version. |
| `GET` | `/health/pool` | SQLAlchemy pool health snapshot. |
| `POST` | `/api/v1/evaluate/compare` | Compare candidate metrics with the active champion. |
| `GET` | `/api/v1/evaluations/` | List recent evaluation runs. |
| `GET` | `/api/v1/evaluations/{run_id}` | Fetch one evaluation run with decision payload. |
| `GET` | `/api/v1/champions/export` | Export active champion metadata. |
| `GET` | `/api/v1/champions/{model_name}` | Fetch the active champion for a model. |
| `POST` | `/api/v1/champions/{model_name}/promote` | Promote a run to champion. |
| `GET` | `/api/v1/champions/{model_name}/previous` | Fetch the previous inactive champion. |
| `GET` | `/api/v1/champions/{model_name}/history` | List champion history for a model. |
| `GET` | `/api/v1/gate/config` | Return current gate configuration snapshot. |
| `POST` | `/api/v1/gate/simulate` | Re-run a saved run against override thresholds. |
| `POST` | `/api/v1/drift/reports` | Persist a drift report. |
| `GET` | `/api/v1/drift/reports` | List drift reports, optionally filtered by `model_name`. |
| `GET` | `/metrics` | Prometheus metrics. |

### CLI and automation commands

| Command | Purpose |
|---|---|
| `make dev` / `make.cmd dev` | Start Docker Compose services. |
| `make build` / `make.cmd build` | Build API, worker, and dashboard images. |
| `make lint` / `make.cmd lint` | Run Ruff and Mypy. |
| `make test-unit` / `make.cmd test-unit` | Run non-integration, non-e2e tests with xdist. |
| `make test-integration` / `make.cmd test-integration` | Run integration tests. |
| `make test-e2e` / `make.cmd test-e2e` | Run e2e tests. |
| `make test-all` / `make.cmd test-all` | Run tests with XML and coverage reports. |
| `make migrate` / `make.cmd migrate` | Apply Alembic migrations. |
| `make migrate-down` / `make.cmd migrate-down` | Roll back one Alembic migration. |
| `make eval` / `make.cmd eval` | Evaluate `models/candidate.json` on the validation split. |
| `make dashboard` / `make.cmd dashboard` | Start Streamlit. |
| `make verify` / `make.cmd verify` | Run the canonical repository verification gate. |
| `make benchmark` | Run benchmark tests under `tests/performance`. |
| `python scripts/seed_golden_set.py` | Generate bundled golden-set CSVs and slice views. |
| `python scripts/pin_golden_checksums.py` | Write current split checksums into `ares.config.yaml`. |
| `python scripts/seed_champion.py` | Train and register the baseline champion. |
| `python scripts/seed_demo_data.py` | Create demo runs and drift reports for the dashboard. |
| `python scripts/run_evaluation.py --help` | Show evaluation CLI flags. |
| `python scripts/run_drift_check.py` | Generate `reports/drift_report.json`. |
| `python scripts/manage_api_keys.py create --name NAME` | Create a DB-backed API key. |
| `python scripts/backup.py --output reports/ares-backup.json` | Create a metadata backup manifest. |
| `python scripts/restore.py reports/ares-backup.json` | Validate a backup manifest before restore. |
| `python scripts/rollback.py --model-name MODEL` | Promote the previous champion for a model. |
| `python scripts/run_adult_income_evaluation.py --help` | Run the Adult-income evidence workflow. |

### Evaluation CLI flags

| Flag | Required | Default | Description |
|---|---|---|---|
| `--model-path` | yes | none | Candidate model path. |
| `--commit-sha` | yes | none | Commit SHA recorded for idempotency and reporting. |
| `--model-name` | no | `default-model` | Logical model name. |
| `--model-version` | no | `candidate` | Candidate version label. |
| `--split` | no | `val` | Golden-set split: `val` or `test`. |
| `--dataset-path` | no | derived from split | Override CSV path. |
| `--output-json` | yes | none | Output result JSON path. |
| `--pr-number` | no | none | Pull request number recorded on the evaluation run. |
| `--run-deepchecks` | no | `false` | Run optional Deepchecks summaries when installed. |

## Roadmap

- [x] Initial ARES reference implementation scaffold.
- [x] FastAPI service, API schemas, rate limiting, auth, and health endpoints.
- [x] Alembic-managed schema for evaluations, champions, drift reports, API keys, webhooks, and audit logs.
- [x] Evaluation CLI, DVC evaluate stage, idempotent DB writes, MLflow artifact logging, and JSON result output.
- [x] Regression gate rules with decision narratives, critical-slice checks, and significance checks.
- [x] Streamlit dashboard pages for leaderboard, drill-down, drift, comparison, promotion, and alerts.
- [x] Docker Compose stack and GitHub Actions workflows for quality, regression gate, drift monitor, and eval-image build.
- [ ] Replace placeholder README/dashboard screenshots with captured assets from `docs/screenshots.md`.
- [ ] Expand evaluator library beyond the current classification/regression/detection surfaces.
- [ ] Deepen production drift automation and alert delivery beyond persisted drift reports and dashboard test reports.
- [ ] Harden release workflow and public open-source onboarding assets.

## Contributing

1. Fork the repository.
2. Clone your fork and create a branch:

```bash
git clone https://github.com/<your-username>/Ares.git
cd Ares
git checkout -b feat/your-change
```

3. Install dependencies and hooks:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev,eval,dashboard]"
pre-commit install
```

4. Make the change with tests and documentation.
5. Run verification before opening a PR:

```bash
make lint
make test-unit
make test-integration
make test-all
make verify
```

6. Open a pull request with the exact commands run and outcomes.

See [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/agent-workflow.md`](docs/agent-workflow.md), and [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) for repository-specific expectations.

## License

ARES is released under the MIT License.

```text
MIT License

Copyright (c) 2026 Ares Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files, to deal in the Software
without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, subject to inclusion of this notice.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

## Acknowledgements

ARES is built on:

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-59666C?style=flat-square)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?style=flat-square)
![DVC](https://img.shields.io/badge/DVC-13ADC7?style=flat-square&logo=dvc&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat-square&logo=scikitlearn&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)

README structure was informed by the public examples and patterns in [Awesome README](https://github.com/matiassingers/awesome-readme), [Best README Template](https://github.com/othneildrew/Best-README-Template), [VS Code](https://github.com/microsoft/vscode), [esbuild](https://github.com/evanw/esbuild), [TC39 proposals](https://github.com/tc39/proposals), and [readme.so](https://readme.so/).
