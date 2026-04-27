# ARES — Model Regression Detection System
## Master Agent Instruction Document (v1.0)
### For: Copilot / Codex / Cline / Windsurf / Cursor

---

> **PRIME DIRECTIVE:** You are building **Ares** — a production-grade, world-class Model Regression Detection System. Every decision must be made at the level of a Principal Engineer at a top-tier AI company. There are no shortcuts. There is no "good enough." The standard is: could this be open-sourced tomorrow and become the industry reference implementation?

---

## 0. TECH STACK — NON-NEGOTIABLE CHOICES

| Layer | Technology | Why |
|---|---|---|
| Language | Python 3.11+ | Type hints, match-case, async improvements |
| API Framework | FastAPI + Pydantic v2 | Speed, auto-docs, strict validation |
| DB | PostgreSQL 16 via Supabase | History, relations, real-time capabilities |
| ORM | SQLAlchemy 2.0 (async) | Async-native, type-safe queries |
| Data Versioning | DVC 3.x + S3/GCS remote | Reproducible datasets as code |
| Experiment Tracking | MLflow 2.x | Model registry, artifact storage |
| Dashboard | Streamlit 1.3x | Fast iteration on internal tooling |
| CI/CD | GitHub Actions | Native PR integration |
| Containerization | Docker + docker-compose | Env parity: dev = prod |
| Testing | Pytest + pytest-asyncio | Async test support |
| ML Validation | Deepchecks 0.18+ | Specialized ML test suites |
| Monitoring | Evidently AI | Drift detection in production |
| Task Queue | Celery + Redis | Async eval jobs for large models |
| Secrets | GitHub Secrets + python-dotenv | Zero hardcoded credentials |
| Notifications | Slack Webhooks (via httpx) | Real-time PR + prod alerts |

---

## 1. REPOSITORY STRUCTURE

Instruct the agent to create this **exact** directory structure. Do not deviate.

```
ares/
├── .github/
│   ├── workflows/
│   │   ├── regression_gate.yml       # Main CI pipeline
│   │   └── drift_monitor.yml         # Nightly drift check
│   └── PULL_REQUEST_TEMPLATE.md      # Auto-populated model card
│
├── ares/                             # Core Python package
│   ├── __init__.py
│   ├── config.py                     # Pydantic Settings (env-based)
│   ├── models/                       # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── evaluation_run.py
│   │   └── model_champion.py
│   ├── evaluators/                   # The "Evaluation Brain"
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract BaseEvaluator class
│   │   ├── classification.py
│   │   ├── detection.py
│   │   └── regression.py
│   ├── metrics/                      # Statistical computation
│   │   ├── __init__.py
│   │   ├── significance.py           # SE, p-values, confidence intervals
│   │   ├── slice_analysis.py         # Per-category breakdown
│   │   └── drift.py                  # KL divergence, PSI
│   ├── gate/                         # Pass/Fail logic
│   │   ├── __init__.py
│   │   ├── rules_engine.py           # Configurable threshold rules
│   │   └── decision.py               # Final PASS/FAIL + report
│   ├── api/                          # FastAPI service
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── evaluations.py
│   │   │   ├── champions.py
│   │   │   └── health.py
│   │   └── schemas/                  # Pydantic request/response schemas
│   │       ├── evaluation.py
│   │       └── champion.py
│   ├── db/                           # Database layer
│   │   ├── __init__.py
│   │   ├── session.py                # Async engine + session factory
│   │   └── crud.py                   # Typed CRUD operations
│   ├── notifier/                     # Slack/GitHub PR comments
│   │   ├── __init__.py
│   │   ├── slack.py
│   │   └── github_pr.py
│   └── worker/                       # Celery tasks
│       ├── __init__.py
│       └── tasks.py
│
├── data/
│   ├── golden_set/                   # DVC-tracked golden dataset
│   │   ├── train.csv.dvc
│   │   ├── val.csv.dvc
│   │   └── slices/                   # Per-category slice files
│   │       ├── edge_cases.csv.dvc
│   │       └── critical.csv.dvc
│   └── schemas/
│       └── data_contract.json        # JSON Schema for I/O validation
│
├── dashboard/
│   ├── app.py                        # Streamlit entry point
│   ├── pages/
│   │   ├── 01_leaderboard.py
│   │   ├── 02_drill_down.py
│   │   └── 03_drift_monitor.py
│   └── components/
│       └── charts.py
│
├── tests/
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/
│   │   ├── test_metrics.py
│   │   ├── test_gate.py
│   │   └── test_significance.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_db.py
│   └── e2e/
│       └── test_full_pipeline.py
│
├── scripts/
│   ├── seed_golden_set.py            # One-time dataset setup
│   ├── run_evaluation.py             # Manual eval trigger
│   └── rollback.py                  # Emergency rollback script
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── Dockerfile.eval              # CI evaluation runner
│
├── docker-compose.yml               # Full local stack
├── docker-compose.ci.yml            # CI-only, no volumes
├── alembic/                         # DB migrations
│   ├── env.py
│   └── versions/
├── alembic.ini
├── pyproject.toml                   # Single source of truth for deps
├── .dvcconfig
├── dvc.yaml                         # DVC pipeline stages
├── ares.config.yaml                 # Ares threshold configuration
└── README.md
```

---

## 2. PHASE I — THE DATA BEDROCK

### 2.1 Golden Dataset Schema

The agent must create `data/schemas/data_contract.json` with this JSON Schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AresDataContract",
  "type": "object",
  "required": ["id", "input", "expected_output", "metadata"],
  "properties": {
    "id": { "type": "string", "format": "uuid" },
    "input": { "type": "object" },
    "expected_output": {
      "type": "object",
      "required": ["label", "confidence"],
      "properties": {
        "label": { "type": "string" },
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },
    "metadata": {
      "type": "object",
      "required": ["slice", "difficulty", "created_at"],
      "properties": {
        "slice": {
          "type": "string",
          "enum": ["easy", "typical", "edge_case", "critical"]
        },
        "difficulty": { "type": "integer", "minimum": 1, "maximum": 5 },
        "created_at": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

### 2.2 DVC Setup Commands

The agent must run these in sequence:

```bash
pip install dvc[s3]  # or dvc[gs] for GCS
dvc init
dvc remote add -d ares-remote s3://your-bucket/ares-data
dvc remote modify ares-remote access_key_id ${AWS_ACCESS_KEY_ID}
dvc remote modify ares-remote secret_access_key ${AWS_SECRET_ACCESS_KEY}

# After placing data in data/golden_set/
dvc add data/golden_set/train.csv
dvc add data/golden_set/val.csv
git add data/golden_set/*.dvc .dvcignore
git commit -m "feat(data): add golden set v1.0"
dvc push
```

### 2.3 Dataset Composition Rule (enforced in code)

In `scripts/seed_golden_set.py`, the agent must validate:
- 10% easy cases (slice = "easy")
- 70% typical cases (slice = "typical")
- 20% edge cases (slice = "edge_case" OR "critical")
- CRITICAL slices must be flagged — any model failing >40% of these is an instant FAIL regardless of overall metrics

---

## 3. PHASE II — THE EVALUATION BRAIN

### 3.1 BaseEvaluator (ares/evaluators/base.py)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass
class EvaluationResult:
    model_id: str
    commit_sha: str
    overall_metrics: dict[str, float]
    slice_metrics: dict[str, dict[str, float]]
    latency_p50_ms: float
    latency_p99_ms: float
    passed: bool
    failure_reason: str | None
    raw_predictions: list[Any]


class BaseEvaluator(ABC):
    def __init__(self, model_path: str, config: dict):
        self.model_path = model_path
        self.config = config
        self._model = None

    @abstractmethod
    def load_model(self) -> None:
        """Load model into self._model. Must be idempotent."""

    @abstractmethod
    def predict(self, inputs: list[Any]) -> list[Any]:
        """Run inference. Return predictions in the same order as inputs."""

    @abstractmethod
    def compute_metrics(
        self, predictions: list[Any], ground_truth: list[Any]
    ) -> dict[str, float]:
        """Return dict of metric_name -> float value."""

    def evaluate(self, dataset: pd.DataFrame) -> EvaluationResult:
        """Orchestrates full evaluation. Do NOT override this."""
        raise NotImplementedError("Implement in evaluate.py orchestrator")
```

### 3.2 Statistical Significance Module (ares/metrics/significance.py)

The agent must implement ALL of the following:

```python
import numpy as np
from scipy import stats


def standard_error(p: float, n: int) -> float:
    """SE = sqrt(p(1-p)/n)"""
    return np.sqrt(p * (1 - p) / n)


def is_improvement_significant(
    new_score: float,
    baseline_score: float,
    n: int,
    alpha: float = 0.05
) -> tuple[bool, float]:
    """
    One-sided z-test: is new_score significantly better than baseline?
    Returns (is_significant, p_value)
    """
    se = standard_error(baseline_score, n)
    if se == 0:
        return new_score > baseline_score, 0.0
    z = (new_score - baseline_score) / se
    p_value = 1 - stats.norm.cdf(z)
    return p_value < alpha, p_value


def wilson_confidence_interval(
    successes: int, n: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Wilson score interval — more accurate than normal approximation."""
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    p_hat = successes / n
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    margin = (z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2))) / denominator
    return center - margin, center + margin


def cohens_h(p1: float, p2: float) -> float:
    """Effect size for proportion difference."""
    return 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
```

### 3.3 Slice Analysis (ares/metrics/slice_analysis.py)

```python
from dataclasses import dataclass
import pandas as pd


@dataclass
class SliceResult:
    slice_name: str
    n_samples: int
    metrics: dict[str, float]
    is_critical: bool
    passed_critical_threshold: bool


def evaluate_slices(
    df: pd.DataFrame,
    predictions: list,
    slice_column: str = "slice",
    critical_slices: list[str] | None = None,
    critical_threshold: float = 0.60,
    metric_fn: callable = None,
) -> dict[str, SliceResult]:
    """
    Evaluate metrics per slice. Critical slices must exceed critical_threshold
    or the entire evaluation is marked as FAILED.
    """
    critical_slices = critical_slices or ["critical", "edge_case"]
    results = {}

    for slice_name in df[slice_column].unique():
        mask = df[slice_column] == slice_name
        slice_df = df[mask]
        slice_preds = [p for p, m in zip(predictions, mask) if m]

        metrics = metric_fn(slice_preds, slice_df["expected_label"].tolist())
        is_critical = slice_name in critical_slices
        primary_metric = list(metrics.values())[0]

        results[slice_name] = SliceResult(
            slice_name=slice_name,
            n_samples=len(slice_df),
            metrics=metrics,
            is_critical=is_critical,
            passed_critical_threshold=(
                primary_metric >= critical_threshold if is_critical else True
            ),
        )

    return results
```

---

## 4. PHASE III — THE MEMORY LAYER

### 4.1 Database Schema (SQLAlchemy models)

**ares/models/evaluation_run.py:**

```python
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, JSON, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import uuid


class Base(DeclarativeBase):
    pass


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    branch: Mapped[str] = mapped_column(String(256), nullable=False)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Core metrics
    overall_f1: Mapped[float] = mapped_column(Float, nullable=False)
    overall_accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    overall_precision: Mapped[float] = mapped_column(Float, nullable=False)
    overall_recall: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance
    latency_p50_ms: Mapped[float] = mapped_column(Float, nullable=False)
    latency_p99_ms: Mapped[float] = mapped_column(Float, nullable=False)
    model_size_mb: Mapped[float] = mapped_column(Float, nullable=False)

    # Slice results (JSON blob for flexibility)
    slice_metrics: Mapped[dict] = mapped_column(JSON, nullable=False, default={})

    # Gate decision
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Dataset fingerprint (for reproducibility)
    golden_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    n_samples_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)


class ModelChampion(Base):
    __tablename__ = "model_champions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    champion_run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.id"))
    promoted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    promoted_by: Mapped[str] = mapped_column(String(256), nullable=False)  # "ci" or user
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

### 4.2 Comparison API Endpoint

In `ares/api/routers/evaluations.py`, implement:

```python
@router.post("/evaluate/compare", response_model=ComparisonResponse)
async def compare_with_champion(
    payload: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Core endpoint. Takes new evaluation metrics, compares against
    current champion, returns PASS/FAIL with full breakdown.
    """
    champion = await crud.get_active_champion(db, payload.model_name)

    if champion is None:
        # No champion exists — first run always passes
        return ComparisonResponse(
            decision="PASS",
            reason="No champion exists. This run becomes the baseline.",
            delta_metrics={},
            is_first_run=True,
        )

    champion_run = await crud.get_evaluation_run(db, champion.champion_run_id)
    decision = rules_engine.evaluate(payload.new_metrics, champion_run, payload.slice_metrics)

    return ComparisonResponse(
        decision=decision.verdict,
        reason=decision.reason,
        delta_metrics=decision.deltas,
        champion_metrics={
            "overall_f1": champion_run.overall_f1,
            "overall_accuracy": champion_run.overall_accuracy,
        },
        new_metrics=payload.new_metrics,
        slice_regressions=decision.slice_regressions,
        is_first_run=False,
    )
```

### 4.3 Rules Engine (ares/gate/rules_engine.py)

All thresholds must be configurable via `ares.config.yaml`:

```yaml
# ares.config.yaml
gate:
  # A model must NOT drop more than this from champion
  max_regression_f1: 0.02          # absolute drop
  max_regression_accuracy: 0.015
  
  # Critical slices hard floor — instant FAIL regardless
  critical_slice_min_f1: 0.60
  
  # Latency: must not be more than 20% slower than champion
  max_latency_regression_pct: 0.20
  
  # Statistical significance: improvements must be real
  significance_alpha: 0.05
  
  # Model bloat: size must not increase more than 15%
  max_size_increase_pct: 0.15

drift:
  kl_divergence_alert_threshold: 0.1
  psi_alert_threshold: 0.2
  production_error_spike_pct: 0.10  # 10% spike triggers rollback
```

---

## 5. PHASE IV — THE CI/CD GATEKEEPER

### 5.1 GitHub Actions Workflow (.github/workflows/regression_gate.yml)

The agent must generate this workflow **exactly**:

```yaml
name: Ares Regression Gate

on:
  pull_request:
    branches: [main]
    paths:
      - 'models/**'
      - 'ares/**'
      - 'data/**/*.dvc'

concurrency:
  group: ares-gate-${{ github.ref }}
  cancel-in-progress: true

jobs:
  regression-gate:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/${{ github.repository }}/ares-eval:latest
      credentials:
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for DVC

      - name: Configure DVC Remote
        run: dvc remote modify ares-remote access_key_id ${{ secrets.AWS_ACCESS_KEY_ID }}
        env:
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Pull Golden Dataset
        run: dvc pull data/golden_set/

      - name: Run Ares Evaluation
        id: ares_eval
        env:
          ARES_DB_URL: ${{ secrets.ARES_DB_URL }}
          ARES_API_KEY: ${{ secrets.ARES_API_KEY }}
          COMMIT_SHA: ${{ github.sha }}
          PR_NUMBER: ${{ github.event.number }}
          MODEL_PATH: ${{ github.workspace }}/models/candidate/
        run: |
          python scripts/run_evaluation.py \
            --model-path $MODEL_PATH \
            --commit-sha $COMMIT_SHA \
            --pr-number $PR_NUMBER \
            --output-json /tmp/ares_result.json

      - name: Post PR Comment
        uses: actions/github-script@v7
        if: always()
        with:
          script: |
            const fs = require('fs');
            const result = JSON.parse(fs.readFileSync('/tmp/ares_result.json', 'utf8'));
            const icon = result.passed ? '✅' : '❌';
            const title = result.passed ? 'Ares Gate: PASSED' : 'Ares Gate: REGRESSION DETECTED';

            let body = `## ${icon} ${title}\n\n`;
            body += `| Metric | Champion | Candidate | Delta |\n|---|---|---|---|\n`;

            for (const [metric, values] of Object.entries(result.metric_table)) {
              const delta = values.delta >= 0 ? `+${values.delta.toFixed(4)}` : values.delta.toFixed(4);
              const emoji = values.delta >= 0 ? '🟢' : '🔴';
              body += `| ${metric} | ${values.champion.toFixed(4)} | ${values.candidate.toFixed(4)} | ${emoji} ${delta} |\n`;
            }

            if (result.slice_regressions && result.slice_regressions.length > 0) {
              body += `\n### ⚠️ Slice Regressions\n`;
              for (const s of result.slice_regressions) {
                body += `- **${s.slice}**: F1 dropped from \`${s.champion_f1.toFixed(4)}\` to \`${s.candidate_f1.toFixed(4)}\`\n`;
              }
            }

            body += `\n<sub>Ares v1 • Run: \`${{ github.sha }}\`</sub>`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body
            });

      - name: Fail if Regression
        if: steps.ares_eval.outputs.passed != 'true'
        run: |
          echo "::error::Ares Gate FAILED. See PR comment for details."
          exit 1
```

### 5.2 Docker Evaluation Container (docker/Dockerfile.eval)

```dockerfile
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl awscli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (cached layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[eval]"

# Install DVC
RUN pip install --no-cache-dir dvc[s3]

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

---

## 6. PHASE V — PRODUCTION POLISH

### 6.1 Drift Detection (ares/metrics/drift.py)

```python
import numpy as np
from scipy.stats import entropy
from dataclasses import dataclass


@dataclass
class DriftReport:
    feature: str
    kl_divergence: float
    psi: float
    is_alerting: bool
    severity: str  # "none", "warning", "critical"


def kl_divergence(p: np.ndarray, q: np.ndarray, epsilon: float = 1e-10) -> float:
    """
    KL Divergence D_KL(P || Q).
    Measures how much the live distribution P diverges from golden set Q.
    epsilon prevents log(0).
    """
    p = np.asarray(p, dtype=float) + epsilon
    q = np.asarray(q, dtype=float) + epsilon
    p /= p.sum()
    q /= q.sum()
    return float(entropy(p, q))


def population_stability_index(
    expected: np.ndarray, actual: np.ndarray, n_bins: int = 10
) -> float:
    """
    PSI — industry-standard drift metric used in banking/finance.
    PSI < 0.1: no drift
    PSI 0.1-0.2: moderate drift (alert)
    PSI > 0.2: significant drift (critical)
    """
    breakpoints = np.percentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)

    expected_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_pct = np.histogram(actual, bins=breakpoints)[0] / len(actual)

    expected_pct = np.where(expected_pct == 0, 1e-4, expected_pct)
    actual_pct = np.where(actual_pct == 0, 1e-4, actual_pct)

    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)


def compute_drift_report(
    feature_name: str,
    golden_distribution: np.ndarray,
    live_distribution: np.ndarray,
    kl_threshold: float = 0.1,
    psi_threshold: float = 0.2,
) -> DriftReport:
    kl = kl_divergence(live_distribution, golden_distribution)
    psi = population_stability_index(golden_distribution, live_distribution)
    is_alerting = kl > kl_threshold or psi > psi_threshold
    severity = "none"
    if psi > 0.2 or kl > 0.15:
        severity = "critical"
    elif psi > 0.1 or kl > 0.1:
        severity = "warning"

    return DriftReport(
        feature=feature_name,
        kl_divergence=kl,
        psi=psi,
        is_alerting=is_alerting,
        severity=severity,
    )
```

### 6.2 Automated Rollback Script (scripts/rollback.py)

```python
#!/usr/bin/env python3
"""
Emergency rollback. Called automatically if production error spike detected.
Can also be invoked manually: python scripts/rollback.py --model-name my_model
"""
import asyncio
import argparse
import httpx
from ares.config import settings


async def rollback(model_name: str, reason: str):
    async with httpx.AsyncClient() as client:
        # 1. Get previous champion from Ares API
        resp = await client.get(
            f"{settings.ARES_API_URL}/champions/{model_name}/previous",
            headers={"X-API-Key": settings.ARES_API_KEY},
        )
        resp.raise_for_status()
        previous = resp.json()

        # 2. Promote previous champion
        await client.post(
            f"{settings.ARES_API_URL}/champions/{model_name}/promote",
            json={
                "run_id": previous["champion_run_id"],
                "promoted_by": "automated_rollback",
                "reason": reason,
            },
            headers={"X-API-Key": settings.ARES_API_KEY},
        )

        # 3. Notify Slack
        await client.post(
            settings.SLACK_WEBHOOK_URL,
            json={
                "text": f"🚨 *ARES AUTO-ROLLBACK*\n"
                        f"Model: `{model_name}`\n"
                        f"Reason: {reason}\n"
                        f"Reverted to: `{previous['model_version']}`"
            },
        )
        print(f"✅ Rollback complete. Reverted {model_name} to {previous['model_version']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--reason", default="Automated: production error spike detected")
    args = parser.parse_args()
    asyncio.run(rollback(args.model_name, args.reason))
```

---

## 7. STREAMLIT DASHBOARD (dashboard/app.py)

The agent must implement a multi-page Streamlit app with:

**Page 1: Leaderboard**
- Time-series line chart: F1 score over last 50 runs (by commit date)
- Champion badge — currently deployed model highlighted
- Filterable table: all runs with pass/fail status, sortable by any metric
- Color coding: green rows = passed, red = failed

**Page 2: Drill Down**
- Select any evaluation run from a dropdown
- Radar chart: all metrics for that run vs. champion
- Slice breakdown bar chart: metric per slice category
- Statistical significance badges (show p-values + confidence intervals)

**Page 3: Drift Monitor**
- Live PSI scores per feature (red/amber/green)
- KL divergence trend over time
- Auto-refresh every 5 minutes (`st.rerun()` with sleep)

---

## 8. CONFIGURATION (ares/config.py)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class AresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # API
    ARES_API_KEY: str
    ARES_API_URL: str = "http://localhost:8000"

    # Storage
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET: str = ""

    # Notifications
    SLACK_WEBHOOK_URL: str = ""
    GITHUB_TOKEN: str = ""

    # Gate Thresholds (can override ares.config.yaml)
    MAX_REGRESSION_F1: float = 0.02
    CRITICAL_SLICE_MIN_F1: float = 0.60
    MAX_LATENCY_REGRESSION_PCT: float = 0.20


settings = AresSettings()
```

---

## 9. TESTING REQUIREMENTS

The agent must achieve:
- **Unit tests**: 90%+ coverage of `ares/metrics/` and `ares/gate/`
- **Integration tests**: All API endpoints tested with a real (test) PostgreSQL
- **E2E test**: Full pipeline from raw input → prediction → comparison → DB write → decision

### Critical Tests the Agent Must Write

```python
# tests/unit/test_gate.py

def test_critical_slice_failure_overrides_passing_overall():
    """
    If overall F1 is above threshold but a critical slice fails,
    the gate MUST return FAIL.
    """
    ...

def test_first_run_always_passes():
    """No champion = first run is always PASS."""
    ...

def test_statistically_insignificant_improvement_does_not_promote():
    """
    A 0.001 improvement on n=100 samples should NOT be treated
    as a real improvement.
    """
    ...

def test_regression_within_tolerance_passes():
    """
    A drop of 0.005 when threshold is 0.02 must PASS.
    """
    ...
```

---

## 10. PYPROJECT.TOML DEPENDENCIES

```toml
[project]
name = "ares"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "sqlalchemy[asyncio]>=2.0.29",
    "asyncpg>=0.29.0",
    "alembic>=1.13.1",
    "httpx>=0.27.0",
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "scipy>=1.13.0",
    "scikit-learn>=1.4.0",
    "deepchecks>=0.18.0",
    "evidently>=0.4.0",
    "mlflow>=2.12.0",
    "streamlit>=1.33.0",
    "plotly>=5.21.0",
    "celery[redis]>=5.3.6",
    "redis>=5.0.3",
    "python-dotenv>=1.0.1",
    "structlog>=24.1.0",
    "prometheus-fastapi-instrumentator>=6.1.0",
]

[project.optional-dependencies]
eval = [
    "torch>=2.2.0",
    "torchvision>=0.17.0",
    "dvc[s3]>=3.49.0",
]
dev = [
    "pytest>=8.1.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "factory-boy>=3.3.0",
    "ruff>=0.4.0",
    "mypy>=1.9.0",
]
```

---

## 11. AGENT EXECUTION ORDER

**Tell your agent to build in this exact order. Do not skip steps.**

1. `pyproject.toml` + `ares/config.py` — foundation, everything else imports from here
2. `ares/models/` — DB schema before any logic
3. `alembic/` setup + `create initial migration`
4. `ares/db/session.py` + `ares/db/crud.py`
5. `ares/metrics/significance.py` + `ares/metrics/slice_analysis.py` + `ares/metrics/drift.py`
6. `ares/evaluators/base.py` + concrete evaluators
7. `ares/gate/rules_engine.py` + `ares/gate/decision.py`
8. `ares/api/` (FastAPI app, routers, schemas)
9. `ares/notifier/` (Slack + GitHub PR)
10. `ares/worker/tasks.py` (Celery)
11. `scripts/run_evaluation.py` (the CLI entrypoint)
12. `docker/` + `docker-compose.yml`
13. `.github/workflows/regression_gate.yml`
14. `dashboard/` (Streamlit)
15. `tests/` (unit → integration → e2e)
16. `data/schemas/data_contract.json` + DVC setup
17. `README.md` — comprehensive, with badges

---

## 12. README REQUIREMENTS

The README must include:
- Architecture diagram (Mermaid)
- Quick start (5 commands from clone to running locally)
- How to add a new model type (evaluator guide)
- How to configure thresholds (`ares.config.yaml` reference)
- CI/CD integration guide
- Dashboard screenshot placeholder
- Badges: CI status, Python version, license, coverage

---

## 13. WHAT MAKES ARES 0.01% — THE NON-OBVIOUS DETAILS

These are the things junior engineers skip. The agent must implement ALL of them:

1. **Structured logging everywhere** — use `structlog` with JSON output. Every evaluation emits: `commit_sha`, `model_name`, `duration_ms`, `passed`, `slice_failures`. No `print()` statements in library code.

2. **Prometheus metrics** — instrument the FastAPI app. Expose `/metrics`. Track: `ares_evaluations_total`, `ares_gate_decisions_total{result="pass|fail"}`, `ares_evaluation_duration_seconds`.

3. **Idempotent evaluations** — if the same `commit_sha` + `golden_set_version` already exists in the DB, return the cached result instead of re-running. Saves CI time.

4. **Async everything** — DB calls, HTTP calls, file I/O. Never block the event loop.

5. **Alembic migrations** — every schema change goes through a migration. No `create_all()` in production code.

6. **API versioning** — prefix all routes with `/api/v1/`. Plan for `/api/v2/`.

7. **Health check endpoint** — `GET /health` returns `{"status": "healthy", "db": "connected", "version": "1.0.0"}`. Required for K8s readiness probe.

8. **Model size tracking** — log `model_size_mb` to the DB. Alert if a new model is 15%+ larger than champion without a corresponding accuracy gain.

9. **DVC pipeline** — define evaluation as a DVC stage in `dvc.yaml` so the full data→eval pipeline is reproducible with `dvc repro`.

10. **Soft delete on champions** — never hard-delete a champion. Set `is_active=False`. This enables rollback history forever.

---

*End of Ares Agent Instructions v1.0*
*After the agent generates the plan, return it for review before any code is written.*
