# Threshold Optimization Guide

ARES can simulate gate outcomes over historical runs and recommend regression thresholds.

## CLI

```bash
python scripts/optimize_thresholds.py history.json --output recommendation.json
```

Input is a JSON list:

```json
[
  {
    "candidate_metrics": {"overall_f1": 0.91, "overall_accuracy": 0.92},
    "champion_metrics": {"overall_f1": 0.90, "overall_accuracy": 0.91},
    "should_pass": true
  }
]
```

## API

`POST /api/v1/gate/optimize` accepts the same historical runs and returns `recommended_config`, `pass_rate`, `expected_accuracy`, false-pass/false-fail rates, and evaluated config count.

Use recommendations as candidates. Always run gate simulation and review business impact before changing production thresholds.
