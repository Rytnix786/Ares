# Evaluator Plugin Authoring Guide

ARES evaluator plugins let teams add model-specific evaluation without editing core evaluator modules. Plugins are trusted Python code loaded through the `ares.evaluators` entry-point group.

## Contract

A plugin exposes a Python entry point in the `ares.evaluators` group. The loaded object must be a factory that returns an instance of `BaseEvaluator` when selected for execution.

```python
from pathlib import Path
from typing import Any

import pandas as pd

from ares.evaluators.base import BaseEvaluator, EvaluationResult


class MyEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self.model = Path(self.model_path).read_text(encoding="utf-8")

    def predict(self, dataset: pd.DataFrame) -> list[Any]:
        # The number of predictions must match len(dataset).
        return ["approved" for _ in range(len(dataset))]

    def compute_metrics(self, predictions: list[Any], dataset: pd.DataFrame) -> EvaluationResult:
        return EvaluationResult(
            overall_metrics={"overall_accuracy": 1.0, "overall_f1": 1.0},
            slice_metrics={"all": {"f1": 1.0, "is_critical": True}},
            passed=True,
            failure_reasons=[],
        )


def create_evaluator(model_path: str, config: dict | None = None) -> BaseEvaluator:
    return MyEvaluator(model_path, config or {})
```

Required evaluator methods:

| Method | Requirement |
|---|---|
| `load_model()` | Load model artifacts from `model_path` or plugin config. |
| `predict(dataset)` | Return one prediction per dataset row. |
| `compute_metrics(predictions, dataset)` | Return `EvaluationResult` with overall and slice metrics. |

Expected dataset columns for the built-in evaluation flow are `id`, `input`, `expected_label`, and `slice`. Custom evaluators may read additional columns, but should fail with a clear error if required columns are absent.

## Manifest

The factory may include a manifest:

```python
create_evaluator.ARES_PLUGIN_MANIFEST = {
    "version": "0.1.0",
    "description": "Custom risk evaluator",
    "trusted": True,
}
```

Manifest validation rules:

- Plugin name comes from the entry-point name and may contain letters, digits, `.`, `_`, and `-`.
- `version` must be non-empty.
- `description` must be 512 characters or fewer.
- `trusted` documents operator intent; it does not sandbox the plugin.

If a factory has no manifest, ARES builds a default external manifest with `version="external"`, `trusted=False`, and the entry-point name.

## Package entry point

```toml
[project.entry-points."ares.evaluators"]
custom-risk = "custom_package.evaluator:create_evaluator"
```

Install the package into the same Python environment as the API/worker. Restart the process, then verify discovery:

```bash
curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/evaluators"
```

## Validation and isolation

ARES validates plugin names, versions, and description size before listing a plugin. Bad manifests and entry-point import failures are isolated from built-in evaluators and are not listed.

The `BaseEvaluator` return type is enforced when the evaluator is created for execution, not when `/api/v1/evaluators` lists available plugins. A plugin with a valid manifest but invalid factory return type can appear in discovery and fail when selected, so test the plugin with a real evaluation before release.

Plugins are trusted Python code. ARES does not sandbox plugin execution. Use package review, pinned versions, deployment allowlists outside ARES, and environment isolation as needed.

## Gate and slice expectations

To work well with ARES governance:

- Include `overall_f1` and `overall_accuracy` when available.
- Include critical slice metrics with `is_critical=True` for protected cohorts.
- Keep metric names stable across releases so slice trends remain comparable.
- Respect gate config keys such as `critical_slice_min_f1` when computing failure reasons.

## Test checklist

Before publishing a plugin:

- [ ] Unit-test `load_model`, `predict`, and `compute_metrics`.
- [ ] Verify prediction count equals dataset row count.
- [ ] Run against a dataset with required columns missing and confirm the error is actionable.
- [ ] Confirm `/api/v1/evaluators` lists the plugin after installation.
- [ ] Run a complete evaluation and confirm the plugin returns a valid `EvaluationResult`.
- [ ] Generate a model card and confirm plugin metrics appear in evidence.
