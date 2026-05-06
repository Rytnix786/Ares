# Model Card Guide

ARES generates a model card for every evaluation run. A model card is a governance artifact that combines the evaluation result, gate decision, slice performance, drift context, and champion lineage into a single Markdown document with an embedded JSON payload. It is generated on demand by `ares.model_cards.generate_model_card` and is intended for release review, compliance archives, and incident follow-up.

## When a model card is generated

A model card is produced in three situations:

1. **Explicit API request**: `GET /api/v1/evaluations/{run_id}/model-card` triggers generation on the fly.
2. **Promotion**: `POST /api/v1/champions/{model_name}/promote` auto-generates a card if `run.model_card_uri` is `None` (`ares/api/routers/champions.py:106-113`).
3. **Dashboard inspection**: the model-comparison workflow links card evidence for selected runs.

If the card does not already exist, the API endpoint stores `model_card_uri` and the JSON payload on the evaluation record via `crud.attach_model_card`. Treat model-card generation as a governance evidence operation, not a read-only display step.

## JSON payload schema

`generate_model_card(run, champion=None, drift_reports=None, champion_history=None)` (`ares/model_cards.py:16-58`) returns a `ModelCard` dataclass (`markdown`, `payload`). The payload is a flat dictionary with the following fields:

| Field | Type | Source |
|---|---|---|
| `run_id` | `str` | `EvaluationRun.id` |
| `model_name` | `str` | `EvaluationRun.model_name` |
| `model_version` | `str` | `EvaluationRun.model_version` |
| `commit_sha` | `str` | `EvaluationRun.commit_sha` |
| `golden_set_version` | `str` | `EvaluationRun.golden_set_version` |
| `passed` | `bool` | `bool(EvaluationRun.passed)` |
| `failure_reason` | `str \| None` | `EvaluationRun.failure_reason` |
| `metrics` | `dict[str, float]` | `extract_metrics(run)` — overall f1, accuracy, precision, recall, latency, size |
| `slice_metrics` | `dict[str, Any]` | `EvaluationRun.slice_metrics` or `{}` |
| `gate_config_snapshot` | `dict[str, Any]` | `EvaluationRun.gate_config_snapshot` or `{}` |
| `artifact_uri` | `str \| None` | `EvaluationRun.artifact_uri` |
| `champion_run_id` | `str \| None` | Active champion's `champion_run_id` when present |
| `dataset_lineage` | `dict` | `{golden_set_version, n_samples_evaluated}` |
| `drift_status` | `list[dict]` | Latest drift reports: `{id, feature, severity, is_alerting}` |
| `champion_history` | `list[dict]` | Promotion/rollback records: `{champion_id, run_id, action, promoted_at}` |

## Markdown structure

The generated Markdown (`ares/model_cards.py:59-86`) contains these sections in order:

1. **Header** — `# Model Card: {model_name}`
2. **Summary** — Run ID, version, commit SHA, golden set version, gate result (`PASS`/`FAIL`), failure reason (or `None`)
3. **Metrics** — Bulleted list of every key/value from `extract_metrics`
4. **Dataset Lineage** — Golden set version and sample count
5. **Drift Evidence** — Count of included drift reports
6. **Champion History** — Count of included champion-history entries
7. **JSON Evidence** — The full payload serialized as a fenced `json` block

## How to access a model card

### API

```bash
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/evaluations/$RUN_ID/model-card"
```

Response shape (`ModelCardResponse` in `ares/api/schemas/evaluation.py:130-134`):

```json
{
  "run_id": "run-abc123",
  "markdown": "# Model Card: fraud-v2\n...",
  "payload": { ... }
}
```

### Python client

```python
from ares_client import AresClient

with AresClient("http://localhost:8000/api/v1", api_key="dev-key-1") as client:
    card = client.get_model_card("run-abc123")
    print(card["markdown"])
    print(card["payload"]["passed"])
```

### Dashboard

Open the **Model Comparison** page, select a run, and click the **Model Card** link. The dashboard renders the Markdown directly and offers a download of the JSON payload.

### CLI

There is no standalone CLI for model cards; use the Python client or API.

## Attaching a custom section via the promotion API

The promotion endpoint accepts a `reason` string that becomes `promotion_reason` on the champion record. This reason is surfaced in the champion-history section of the model card. To attach richer custom evidence, submit the evaluation with `metadata_json` containing your custom fields; `generate_model_card` does not currently merge custom metadata, but the JSON payload block preserves everything on the run record.

```bash
curl -X POST "http://localhost:8000/api/v1/champions/fraud-v2/promote" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "run-abc123", "promoted_by": "ci-bot", "reason": "candidate passed all gates with 2% f1 improvement"}'
```

## Golden-file test

The model-card Markdown output is locked by `tests/golden/model_card_default.md`. If the structure or ordering changes, the golden test fails. Update the golden file deliberately and document the reason in the PR. Do not regenerate snapshots to hide a regression.

Current golden-file template (`tests/golden/model_card_default.md`):

```markdown
# Model Card: default-model

- Run ID: `<run_id>`
- Version: `candidate`
- Commit: `<commit_sha>`
- Golden set: `v1.0.0`
- Gate result: PASS
- Failure reason: None
```

## Security and redaction

Model-card metadata may be copied into governance systems. Do not put secrets, raw customer data, private API keys, or sensitive file paths into evaluation metadata, artifact URIs, slice names, or drift payloads. Redact sensitive values before creating the evaluation run.

## Data quality checklist

Before trusting a model card, verify:

- [ ] The run was persisted through the API or evaluation CLI path.
- [ ] `golden_set_version` and `n_samples_evaluated` are set.
- [ ] `gate_config_snapshot` reflects the thresholds in force at evaluation time.
- [ ] Critical slices are present in `slice_metrics`.
- [ ] Drift reports exist when production drift evidence is required.
- [ ] Artifact URIs do not expose secrets or private credentials.
