from __future__ import annotations

from celery import Celery

from ares.config import settings
from ares.observability.telemetry import trace_function
from ares.worker.event_workflow import (
    EvaluationEventRunner,
    EvaluationEventType,
    build_evaluation_requested_event,
)

celery_app = Celery("ares", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.task_always_eager = False


@celery_app.task(name="ares.evaluate")
@trace_function(
    "worker.evaluate_task",
    attributes={
        "worker.task_name": "ares.evaluate",
        "worker.run_id": lambda args, kwargs: str((args[0] or {}).get("run_id") or (args[0] or {}).get("job_id") or ""),
    },
)
def evaluate_task(payload: dict) -> dict:
    job_id = str(payload.get("job_id", "celery-job"))
    event_payload = {key: value for key, value in payload.items() if key != "job_id"}
    event = build_evaluation_requested_event(job_id, **event_payload)
    state = EvaluationEventRunner().run(event)
    return {
        "status": state.status,
        "events": [event.event_type.value for event in state.events],
        "champion_run_id": state.champion_run_id,
        "alert_triggered": state.alert_triggered,
        "completed": state.events[-1].event_type
        in {EvaluationEventType.CHAMPION_PROMOTED, EvaluationEventType.ALERT_TRIGGERED},
    }
