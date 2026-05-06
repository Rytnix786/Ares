# Gate Plugin Guide

ARES gate plugins let teams replace or augment promotion decision policy without editing `ares/gate/rules_engine.py`.

## Contract

Implement an object with:

```python
name = "strict_gate"
version = "1.0.0"

def evaluate(new_metrics, champion_metrics, slice_metrics=None, config=None, n_samples=1):
    ...
```

Return `ares.gate.decision.GateDecision`.

## Entry point

```toml
[project.entry-points."ares.gate_plugins"]
strict = "your_package.gates:StrictGate"
```

## Runtime

```python
from ares.gate.plugins import evaluate_with_plugin

decision = evaluate_with_plugin("strict", candidate, champion)
```

Plugins are trusted Python code. Install only reviewed packages and use allowlists in production configuration where required.
