# Model Card Guide

ARES generates Markdown and JSON model cards from evaluation evidence. Model cards are intended for release review, governance archives, and incident follow-up. They summarize what was evaluated, which gate configuration was used, how slices performed, and how the run relates to champion and drift state.

## Generate a model card

Use the API endpoint:

```bash
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/evaluations/$RUN_ID/model-card"
```

Or use the Python client:

```python
from ares_client import AresClient

with AresClient("http://localhost:8000", api_key="dev-key-1") as client:
    card = client.get_model_card("baseline-seed-run")
    print(card["markdown"])
```

The dashboard model comparison workflow also links model-card evidence for selected runs when available.

## Evidence included

`ares.model_cards.generate_model_card` builds a payload with:

| Field | Source | Purpose |
|---|---|---|
| `run_id` | `EvaluationRun.id` | Stable evaluation identifier. |
| `model_name` | `EvaluationRun.model_name` | Model family under governance. |
| `model_version` | `EvaluationRun.model_version` | Candidate/champion version label. |
| `commit_sha` | `EvaluationRun.commit_sha` | Code/model provenance. |
| `golden_set_version` | `EvaluationRun.golden_set_version` | Dataset lineage. |
| `passed` and `failure_reason` | Gate result fields | Release decision evidence. |
| `metrics` | Presented evaluation metrics | Overall score and operational metrics. |
| `slice_metrics` | Evaluation slice metrics | Critical-slice and subgroup evidence. |
| `gate_config_snapshot` | Evaluation run metadata | Thresholds used at decision time. |
| `artifact_uri` | Evaluation run artifact URI | Link to stored model/evidence artifact. |
| `champion_run_id` | Active champion, when present | Relationship to production champion. |
| `dataset_lineage` | Golden set and sample count | Reproducibility context. |
| `drift_status` | Related drift reports | Production data health context. |
| `champion_history` | Promotion/rollback history | Governance timeline. |

## Markdown sections

The generated Markdown contains:

1. Summary header with model name, run ID, version, commit, golden set, gate result, and failure reason.
2. Metrics list.
3. Dataset lineage section.
4. Drift evidence count.
5. Champion history count.
6. Embedded JSON evidence block for machine archiving.

## Persistence behavior

`GET /api/v1/evaluations/{run_id}/model-card` generates the card and, if the run does not already have card evidence attached, stores `model_card_uri` and JSON payload evidence on the evaluation record. Promotion also attaches missing model-card evidence before completing the champion update. Treat model-card generation as a governance evidence operation, not just a read-only display step.

## When to attach a model card

Attach or archive a model card when:

- Promoting a new champion.
- Rejecting a candidate after a gate failure.
- Rolling back during an incident.
- Changing gate thresholds.
- Reviewing drift or slice degradation.
- Handing off a model release for governance approval.

## Data quality checklist

Before trusting a model card, verify:

- [ ] The run was persisted through the API or evaluation CLI path.
- [ ] `golden_set_version` and `n_samples_evaluated` are set.
- [ ] `gate_config_snapshot` reflects the thresholds in force at evaluation time.
- [ ] Critical slices are present in `slice_metrics`.
- [ ] Drift reports are present when production drift evidence is required.
- [ ] Artifact URIs do not expose secrets or private credentials.

## Redaction and security

Model cards include metadata that may be copied into governance systems. Do not put secrets, raw customer data, private API keys, or sensitive file paths into evaluation metadata, artifact URIs, slice names, or drift payloads. Redact sensitive values before creating the evaluation run.

## Golden-file tests

Model-card output is locked by golden-file tests. If the model-card structure changes, update the golden file deliberately and include the reason in the review. Do not update snapshots to hide a regression.
