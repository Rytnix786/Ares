# Configuration Tuning Guide

ARES gate thresholds are the primary control surface for model promotion. This guide covers every configurable key, how to inspect the live config, how to simulate decisions before committing changes, and how to use the threshold optimizer to find a good configuration from historical evidence.

## Configuration hierarchy

Gate thresholds are read from `ares.config.yaml` under the `gate:` key. If the file is missing or the key is absent, internal defaults apply (`ares/gate/rules_engine.py:24-39`).

### `ares.config.yaml` gate keys

| Key | Default | Unit | What it controls |
|---|---|---|---|
| `max_regression_f1` | `0.02` | absolute | Maximum allowed drop in `overall_f1` vs champion. |
| `max_regression_accuracy` | `0.015` | absolute | Maximum allowed drop in `overall_accuracy` vs champion. |
| `critical_slice_min_f1` | `0.60` | absolute | Minimum `f1` for any slice marked `is_critical=True`. |
| `max_latency_regression_pct` | `10.0` | percentage | Max latency increase vs champion (converted to ratio `0.10` internally). |
| `max_size_increase_pct` | `10.0` | percentage | Max model size increase without accuracy gain (converted to ratio `0.10`). |
| `significance_alpha` | `0.05` | probability | Alpha for statistical significance test on f1 improvement. |

All percentage keys accept either a raw ratio (`0.10`) or a human-readable percentage (`10.0`). The `_as_ratio` helper in `rules_engine.py:12-21` divides values greater than `1.0` by `100` automatically.

Example `ares.config.yaml`:

```yaml
gate:
  max_regression_f1: 0.02
  max_regression_accuracy: 0.015
  critical_slice_min_f1: 0.60
  max_latency_regression_pct: 10.0
  max_size_increase_pct: 10.0
  significance_alpha: 0.05
```

## Read the current gate config

### API

```bash
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/gate/config"
```

Returns the raw `gate` dictionary from `ares.config.yaml` (or empty dict if none exists). This endpoint requires `read` scope.

### Python client

```python
from ares_client import AresClient

with AresClient("http://localhost:8000/api/v1", api_key="dev-key-1") as client:
    config = client.optimize_thresholds([])  # no direct config getter; use API
```

There is no dedicated `get_gate_config` client method; call the API directly or read `ares.config.yaml` on disk.

## Simulate a gate decision before changing thresholds

The simulation endpoint re-evaluates an existing run against overridden thresholds without persisting anything.

### API

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/gate/simulate" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"run_id": "run-abc123", "override_thresholds": {"max_regression_f1": 0.03}}'
```

Request schema (`SimulationRequest` in `ares/api/schemas/evaluation.py:47-49`):

| Field | Type | Required |
|---|---|---|
| `run_id` | `str` | yes |
| `override_thresholds` | `dict[str, float]` | no (default `{}`) |

Response schema (`SimulationResponse` in `ares/api/schemas/evaluation.py:52-53`):

| Field | Type | Meaning |
|---|---|---|
| `run_id` | `str` | The evaluated run |
| `decision` | `str` | `PASS` or `FAIL` |
| `reason` | `str` | Human-readable rationale |
| `should_promote` | `bool` | Whether promotion is recommended |
| `slice_regressions` | `list[dict]` | Which slices failed and by how much |
| `config_snapshot` | `dict` | The thresholds actually used (defaults + overrides) |
| `is_first_run` | `bool` | True when no champion exists |
| `new_metrics` | `dict[str, float]` | Candidate metrics |
| `champion_metrics` | `dict[str, float]` | Champion metrics used for comparison |

### Simulation workflow

1. Run an evaluation: `POST /api/v1/evaluate/compare`
2. Read current config: `GET /api/v1/gate/config`
3. Simulate with one changed key at a time: `POST /api/v1/gate/simulate`
4. Inspect `slice_regressions` and `reason`
5. Update `ares.config.yaml` with the validated values
6. Re-run the evaluation and confirm `decision` matches expectation

## Threshold tuning workflow

A safe tuning cycle looks like this:

1. **Run** — Submit a representative evaluation through `POST /api/v1/evaluate/compare` or the evaluation CLI.
2. **Inspect** — Read `GET /api/v1/gate/config` and compare against the defaults in `rules_engine.py`.
3. **Simulate** — Post `override_thresholds` to `/api/v1/gate/simulate` and confirm the new gate would have produced the desired `decision`.
4. **Adjust** — Edit `ares.config.yaml`, restart the API if necessary, or push the config through your deployment pipeline.
5. **Re-run** — Submit the same evaluation payload again and verify the live gate decision matches the simulation.
6. **Archive** — Generate a model card for the re-run and attach it to release evidence.

## Anti-patterns

### Setting thresholds too tight

The optimizer grid does not explore below `0.005` for f1 or accuracy tolerances. If you set `max_regression_f1: 0.001`, nearly every candidate will fail. Prefer starting with the optimizer defaults and tightening only after collecting enough historical evidence.

### Ignoring slice-level failures

A run can have good overall f1 while a critical slice (`is_critical=True`) falls below `critical_slice_min_f1`. The gate fails in this case. Do not raise the overall threshold and ignore the slice; fix the model or data for that subgroup.

### Changing thresholds without a baseline evaluation run

Never change thresholds without a recent passing run to validate against. If no baseline exists, the simulator cannot compare candidate vs champion, and you are tuning blindly.

## Threshold optimizer

The optimizer searches a grid of threshold combinations and returns the one with the best accuracy on labeled historical runs.

### CLI

```bash
ares-optimize-thresholds history.json --output recommendation.json
```

The `ares-optimize-thresholds` command is registered in `pyproject.toml` under `[project.scripts]`. It expects a JSON file containing a list of historical run objects.

Input format (`ares/cli/thresholds.py:16-23`):

```json
[
  {
    "candidate_metrics": {"overall_f1": 0.91, "overall_accuracy": 0.90},
    "champion_metrics": {"overall_f1": 0.90, "overall_accuracy": 0.89},
    "should_pass": true,
    "slice_metrics": {"critical": {"f1": 0.85, "is_critical": true}}
  }
]
```

Output format (`ares/cli/thresholds.py:26-33`):

```json
{
  "recommended_config": {"max_regression_f1": 0.01, "max_regression_accuracy": 0.015, "critical_slice_min_f1": 0.60},
  "pass_rate": 0.75,
  "expected_accuracy": 0.92,
  "false_pass_rate": 0.05,
  "false_fail_rate": 0.20,
  "evaluated_configs": 48
}
```

### API

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/gate/optimize" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"historical_runs": [...]}'
```

Request schema (`ThresholdOptimizeRequest` in `ares/api/routers/gate.py:33-37`):

| Field | Type | Default grid |
|---|---|---|
| `historical_runs` | `list[ThresholdHistoricalRunPayload]` | required |
| `f1_tolerances` | `list[float] \| None` | `[0.005, 0.01, 0.02, 0.03]` |
| `accuracy_tolerances` | `list[float] \| None` | `[0.005, 0.01, 0.015, 0.02]` |
| `critical_slice_floors` | `list[float] \| None` | `[0.55, 0.60, 0.65]` |

### Interpreting the output

- `recommended_config` — the best-scoring threshold combination.
- `pass_rate` — fraction of historical runs that would pass under the recommended config.
- `expected_accuracy` — fraction of labeled runs where the gate decision matches `should_pass`.
- `false_pass_rate` — labeled runs that should have failed but passed.
- `false_fail_rate` — labeled runs that should have passed but failed.
- `evaluated_configs` — total grid points searched.

### Applying the recommendation

1. Write the `recommended_config` values into `ares.config.yaml` under the `gate:` key.
2. Re-run a representative evaluation.
3. Simulate the new thresholds against the same run to confirm consistency.
4. Archive a model card for the validated configuration.

## Safe rollout checklist

Before committing a tuning change:

- [ ] Record the old and new value.
- [ ] Link the evaluation runs or drift reports that motivated the change.
- [ ] Re-run representative evaluations.
- [ ] Confirm model cards include the new evidence.
- [ ] Check dashboard pages load without console errors on in-app navigation.
- [ ] Run `python scripts/verify_repo.py` before release.
