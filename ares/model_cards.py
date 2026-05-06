from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ares.api.presenters import extract_metrics


@dataclass(frozen=True)
class ModelCard:
    markdown: str
    payload: dict[str, Any]


def generate_model_card(
    run: Any,
    champion: Any | None = None,
    drift_reports: list[Any] | None = None,
    champion_history: list[Any] | None = None,
) -> ModelCard:
    metrics = extract_metrics(run)
    payload = {
        "run_id": run.id,
        "model_name": run.model_name,
        "model_version": run.model_version,
        "commit_sha": run.commit_sha,
        "golden_set_version": run.golden_set_version,
        "passed": bool(run.passed),
        "failure_reason": run.failure_reason,
        "metrics": metrics,
        "slice_metrics": run.slice_metrics or {},
        "gate_config_snapshot": run.gate_config_snapshot or {},
        "artifact_uri": run.artifact_uri,
        "champion_run_id": None if champion is None else champion.champion_run_id,
        "dataset_lineage": {
            "golden_set_version": run.golden_set_version,
            "n_samples_evaluated": getattr(run, "n_samples_evaluated", None),
        },
        "drift_status": [
            {
                "id": getattr(report, "id", None),
                "feature": getattr(report, "feature", None),
                "severity": getattr(report, "severity", None),
                "is_alerting": getattr(report, "is_alerting", None),
            }
            for report in (drift_reports or [])
        ],
        "champion_history": [
            {
                "champion_id": getattr(item, "id", None),
                "run_id": getattr(item, "champion_run_id", None),
                "action": getattr(item, "action", None),
                "promoted_at": None if getattr(item, "promoted_at", None) is None else item.promoted_at.isoformat(),
            }
            for item in (champion_history or [])
        ],
    }
    markdown = "\n".join([
        f"# Model Card: {run.model_name}",
        "",
        f"- Run ID: `{run.id}`",
        f"- Version: `{run.model_version}`",
        f"- Commit: `{run.commit_sha}`",
        f"- Golden set: `{run.golden_set_version}`",
        f"- Gate result: {'PASS' if run.passed else 'FAIL'}",
        f"- Failure reason: {run.failure_reason or 'None'}",
        "",
        "## Metrics",
        *[f"- {key}: {value}" for key, value in metrics.items()],
        "",
        "## Dataset Lineage",
        f"- Golden set version: `{run.golden_set_version}`",
        f"- Samples evaluated: `{getattr(run, 'n_samples_evaluated', 'unknown')}`",
        "",
        "## Drift Evidence",
        f"- Reports included: `{len(drift_reports or [])}`",
        "",
        "## Champion History",
        f"- Entries included: `{len(champion_history or [])}`",
        "",
        "## JSON Evidence",
        "```json",
        json.dumps(payload, indent=2, sort_keys=True),
        "```",
    ])
    return ModelCard(markdown=markdown, payload=payload)
