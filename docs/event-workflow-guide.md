# Event Workflow Guide

Phase 4 adds an importable event workflow runner used by the Celery task surface.

## Event chain

1. `evaluation_requested`
2. `evaluation_running`
3. `gate_decision`
4. `champion_promoted` or `champion_rejected`
5. `alert_triggered` when rejected

The eager runner in `ares.worker.event_workflow` is deterministic and used by integration tests. Celery task `ares.evaluate` wraps the same runner so broker-backed execution and tests share state-transition logic.

## Example

```python
from ares.worker.event_workflow import EvaluationEventRunner, build_evaluation_requested_event

event = build_evaluation_requested_event(
    "job-1",
    candidate_metrics={"overall_f1": 0.91},
    champion_metrics={"overall_f1": 0.90},
)
state = EvaluationEventRunner().run(event)
```
