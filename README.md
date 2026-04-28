# Ares — Model Regression Detection System

![CI](https://img.shields.io/github/actions/workflow/status/Rytnix786/Ares/quality.yml?branch=main&label=CI) ![Coverage](https://img.shields.io/badge/coverage-91%25-brightgreen) ![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Docker](https://img.shields.io/badge/docker-compose-blue)

> Ares decides whether a candidate ML model is safe to replace the current champion before it reaches production.

![Hero GIF placeholder](docs/assets/screenshots/hero-placeholder.png)

## Why Ares Exists

Shipping a model is rarely the hard part. The real operational risk starts after training, when a team needs to prove that a new candidate is better than the current champion, does not regress on critical slices, and will not silently degrade quality in production.

Ares exists to make promotion decisions reproducible, explainable, and automatable. It combines a golden evaluation dataset, explicit gate thresholds, historical champion state, CI-ready evaluation outputs, and an operator dashboard so teams can answer a single high-stakes question with evidence: **should this model ship?**

## Quick Start

These 5 commands work on Windows from a fresh clone and remain safe on repeat runs because `scripts/seed_champion.py` is idempotent.

```cmd
git clone https://github.com/Rytnix786/Ares.git
cd Ares
copy .env.example .env
python -m venv .venv && .venv\Scripts\python -m pip install -e ".[dev,eval,dashboard]"
docker compose up -d && python -m alembic upgrade head && python scripts/seed_champion.py && make verify
```

Local surfaces after startup:

- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`
- MLflow: `http://localhost:5000`
- MinIO console: `http://localhost:9001`

## Core Workflow

1. **Train** a candidate model outside Ares using your existing ML pipeline.
2. **Register** or seed a baseline champion in PostgreSQL.
3. **Evaluate** the candidate against the golden dataset using `scripts/run_evaluation.py`.
4. **Gate** the candidate with metric tolerances, critical-slice floors, and significance checks.
5. **Promote** the candidate only if the decision passes and the evidence is acceptable.

## Architecture

```mermaid
graph TD
    DS[Golden Dataset<br/>DVC-versioned] --> EV[Evaluator<br/>BaseEvaluator]
    CM[Candidate Model] --> EV
    EV --> GA[Gate Engine<br/>Rules + Slices]
    GA --> DB[(PostgreSQL<br/>Champion State)]
    GA --> ML[MLflow<br/>Artifacts]
    GA --> AP[FastAPI<br/>/api/v1]
    AP --> DH[Streamlit<br/>Dashboard]
    AP --> CI[GitHub Actions<br/>PR Gate]
    DB --> DH
    PR[Production<br/>Predictions] --> DR[Drift Monitor<br/>Evidently/KL/PSI]
    DR --> AP
```

## Key Features

- Candidate-vs-champion comparison with pass/fail promotion gates
- Human-readable decision narratives for API, CLI, and dashboard review
- Historical champion timeline and exportable audit trail
- Drift monitoring with PSI/KL reporting and dashboard visibility
- CI/CD-friendly commands for build, verify, evaluate, and smoke-test workflows

## Dashboard

The Streamlit dashboard provides a leaderboard, run drill-down, champion history, and drift visibility for operators.

![Leaderboard placeholder](docs/assets/screenshots/leaderboard-placeholder.png)

Planned screenshot set and capture workflow live in [docs/screenshots.md](docs/screenshots.md).

## API Reference

All versioned application endpoints live under `/api/v1`. Health endpoints remain unversioned at `/health/*`.

### Compare a candidate with the current champion

```bash
curl -X POST http://localhost:8000/api/v1/evaluate/compare \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-1" \
  -d '{
    "model_name": "default-model",
    "commit_sha": "abc123",
    "new_metrics": {
      "overall_f1": 0.91,
      "overall_accuracy": 0.91,
      "latency_p99_ms": 10.0,
      "model_size_mb": 1.0
    },
    "slice_metrics": {
      "critical": {"f1": 0.91, "is_critical": true}
    },
    "n_samples": 100
  }'
```

### List champion history for a model

```bash
curl http://localhost:8000/api/v1/champions/default-model/history \
  -H "X-API-Key: dev-key-1"
```

### Simulate alternate gate thresholds without changing state

```bash
curl -X POST http://localhost:8000/api/v1/gate/simulate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-key-1" \
  -d '{
    "run_id": "demo-run-010",
    "override_thresholds": {
      "max_regression_f1": 0.01,
      "critical_slice_min_f1": 0.70
    }
  }'
```

## Evaluator Extension Guide

Add a new evaluator by subclassing `BaseEvaluator`. In most cases you only need `load_model()`, `predict()`, and `compute_metrics()`.

```python
from typing import Any

from ares.evaluators.base import BaseEvaluator


class MyEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self._model = {"default_label": "positive"}

    def predict(self, inputs: list[Any]) -> list[Any]:
        return [self._model["default_label"] for _ in inputs]

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        return {"overall_accuracy": 1.0, "overall_f1": 1.0, "overall_precision": 1.0, "overall_recall": 1.0}
```

## Deployment Guide

For local Docker and Supabase-backed production, keep configuration limited to these 4 environment variables:

| Variable | Local Docker | Supabase / Hosted |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://ares:ares@localhost:55432/ares` | `postgresql+asyncpg://postgres:<password>@db.<ref>.supabase.co:5432/postgres` |
| `ARES_API_KEYS` | `dev-key-1,dev-key-2` or JSON array | Rotated production key set |
| `ARES_API_URL` | `http://localhost:8000` | Public API root URL |
| `ARES_DASHBOARD_URL` | `http://localhost:8501` | Public dashboard URL |

Notes:

- Container-to-container communication in Compose uses service DNS names such as `db`, `api`, and `dashboard`.
- Do **not** use `localhost` for container-to-container traffic.
- Notification failures must not roll back database state.

## Configuration Reference

Gate thresholds live in `ares.config.yaml`.

| Key | Default | Meaning |
|---|---:|---|
| `max_regression_f1` | `0.02` | Maximum allowed F1 drop vs champion |
| `max_regression_accuracy` | `0.015` | Maximum allowed accuracy drop vs champion |
| `critical_slice_min_f1` | `0.60` | Minimum F1 required on critical slices |
| `max_latency_regression_pct` | `0.20` | Allowed p99 latency regression ratio |
| `significance_alpha` | `0.05` | Statistical significance threshold |
| `max_size_increase_pct` | `0.15` | Allowed model size growth without gain |

## CI/CD Integration

Use Ares inside CI with the canonical commands already used by the repository workflows:

```yaml
- name: Build Ares services
  run: make build

- name: Verify repository
  run: make verify

- name: Evaluate candidate
  run: python scripts/run_evaluation.py --model-path models/candidate.json --commit-sha ${{ github.sha }} --model-name default-model --split val --output-json reports/ares_result.json
```

For promotion-grade decisions, rerun the evaluation with `--split test`.

## Roadmap

- **Current milestone:** critical security fixes, decision narratives, and operator UX hardening
- **Next 3 planned features:** richer demo assets, expanded evaluator library, and deeper production drift automation
- **Longer term:** hardened release workflow, public OSS onboarding polish, and broader audit evidence automation

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for Windows setup, evaluator and gate extension guidance, lint/test commands, and PR evidence requirements.

## Security

See [SECURITY.md](SECURITY.md) and [.github/SECURITY.md](.github/SECURITY.md).

## License

MIT