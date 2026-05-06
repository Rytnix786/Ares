# Evaluator Plugin Authoring Guide

ARES discovers evaluator plugins through Python entry points in the `ares.evaluators` group. A plugin must expose a factory callable that returns a `BaseEvaluator` instance. This guide covers the full contract, how to register a plugin, how to test it locally, and the security trust boundary.

## Plugin contract

### EvaluatorFactory Protocol

```python
from typing import Any, Protocol
from ares.evaluators.base import BaseEvaluator

class EvaluatorFactory(Protocol):
    def __call__(
        self,
        model_path: str,
        config: dict[str, Any] | None = None,
    ) -> BaseEvaluator: ...
```

The factory is called with:

- `model_path` — path to the serialized model artifact (file, URI, or identifier).
- `config` — optional dictionary of evaluator-specific settings (e.g. batch size, feature columns).

The factory must return an instance of a class that inherits from `BaseEvaluator`.

### BaseEvaluator abstract class

```python
class BaseEvaluator(ABC):
    required_columns = {"id", "input", "expected_label", "slice"}

    def __init__(self, model_path: str, config: dict[str, Any] | None = None):
        self.model_path = model_path
        self.config = config or {}
        self._model: Any = None

    @abstractmethod
    def load_model(self) -> None: ...

    @abstractmethod
    def predict(self, inputs: list[Any]) -> list[Any]: ...

    @abstractmethod
    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]: ...

    def evaluate(self, dataset: pd.DataFrame, commit_sha: str = "local") -> EvaluationResult: ...
```

Required methods:

- `load_model()` — Load the model from `self.model_path` into `self._model`.
- `predict(inputs)` — Run inference on a list of raw inputs and return predictions.
- `compute_metrics(predictions, ground_truth)` — Return a dictionary of metric names to float values.

The concrete `evaluate(dataset, commit_sha)` method runs the full pipeline:

1. Validates that `dataset` contains `required_columns`.
2. Calls `load_model()` if `_model` is `None`.
3. Calls `predict()` on `dataset["input"]`.
4. Measures latency.
5. Calls `compute_metrics()` against `dataset["expected_label"]`.
6. Runs per-slice analysis via `evaluate_slices()`.
7. Returns an `EvaluationResult` with `passed` set to `True` only if every critical slice passes its threshold.

### PluginManifest

Plugins may optionally declare a manifest dictionary on the factory callable:

```python
class PluginManifest(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_.-]+$")
    version: str = Field(min_length=1)
    description: str = ""
    trusted: bool = False
    entry_point: str | None = None
```

To attach a manifest, set `ARES_PLUGIN_MANIFEST` on the factory:

```python
def create_evaluator(model_path: str, config: dict[str, Any] | None = None) -> BaseEvaluator:
    return MyEvaluator(model_path, config)

create_evaluator.ARES_PLUGIN_MANIFEST = {
    "version": "1.2.0",
    "description": "My custom evaluator for tabular fraud models",
    "trusted": True,
}
```

If no manifest is provided, the plugin is loaded with `version="external"`, `trusted=False`.

## Register the plugin

### pyproject.toml entry point

Add to your plugin package's `pyproject.toml`:

```toml
[project.entry-points."ares.evaluators"]
my-evaluator = "my_package.evaluator:create_evaluator"
```

The entry-point **name** (`my-evaluator`) must match the manifest `name` if a manifest is provided. The entry-point **value** (`my_package.evaluator:create_evaluator`) is the import path to the factory callable.

### Install in editable mode

```bash
cd my-package
pip install -e .
```

After installation, verify discovery:

```bash
curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/evaluators"
```

The listing endpoint returns `{name, version, description}` for every discovered plugin (`ares/api/routers/evaluations.py:38-42`).

## Test the plugin locally

1. Install your package in the same virtual environment as ARES.
2. Restart the API worker or reload the module.
3. Query `GET /api/v1/evaluators` and confirm your plugin appears with the expected name and version.
4. Trigger an evaluation using your plugin name in the payload.
5. Inspect logs for import errors or manifest validation failures; these are silently skipped during discovery but will surface when the evaluator is instantiated.

## Security trust boundary

Plugins are **trusted code**. They run in the same Python process as the API and worker. There is no sandbox, no restricted filesystem access, and no network isolation. A malicious plugin can:

- Read any file readable by the process.
- Make arbitrary network requests.
- Execute arbitrary code during `import` or `load_model()`.

**Controls**:

- Install only reviewed, signed, or internally authored packages.
- Pin plugin versions in `pyproject.toml` or `requirements.txt`.
- Audit plugin source code before adding it to the entry-point group.
- Treat plugin load failures as release blockers when the plugin is required.

## Complete working example: RandomEvaluator

Below is a minimal evaluator that returns random metrics. It is useful for CI fixtures and integration tests.

```python
from __future__ import annotations

import random
from typing import Any

import pandas as pd
from ares.evaluators.base import BaseEvaluator, EvaluationResult
from ares.metrics.slice_analysis import evaluate_slices


class RandomEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self._model = object()  # no-op

    def predict(self, inputs: list[Any]) -> list[Any]:
        return [random.choice([0, 1]) for _ in inputs]

    def compute_metrics(self, predictions: list[Any], ground_truth: list[Any]) -> dict[str, float]:
        correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        accuracy = correct / max(len(ground_truth), 1)
        return {
            "overall_f1": random.uniform(0.7, 0.95),
            "overall_accuracy": accuracy,
            "overall_precision": random.uniform(0.7, 0.95),
            "overall_recall": random.uniform(0.7, 0.95),
        }


def create_evaluator(model_path: str, config: dict[str, Any] | None = None) -> BaseEvaluator:
    return RandomEvaluator(model_path, config)


create_evaluator.ARES_PLUGIN_MANIFEST = {
    "version": "0.1.0",
    "description": "Random evaluator for integration testing",
    "trusted": False,
}
```

Register it:

```toml
[project.entry-points."ares.evaluators"]
random = "my_package.random_eval:create_evaluator"
```

Then use it:

```bash
curl -X POST "$ARES_API_ORIGIN/api/v1/evaluate/compare" \
  -H "X-API-Key: $ARES_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "test", "commit_sha": "abc", "new_metrics": {"overall_f1": 0.9}}'
```

Note: `RandomEvaluator` does not use a real model; it is intended for testing only.
