from __future__ import annotations

from ares.worker.event_workflow import (
    EvaluationEventRunner,
    EvaluationEventType,
    build_evaluation_requested_event,
)
from ares.worker.tasks import evaluate_task


def test_event_workflow_promotes_passing_candidate() -> None:
    event = build_evaluation_requested_event(
        "job-1",
        run_id="run-1",
        model_name="default-model",
        candidate_metrics={"overall_f1": 0.92, "overall_accuracy": 0.93},
        champion_metrics={"overall_f1": 0.90, "overall_accuracy": 0.91},
        n_samples=1000,
    )

    state = EvaluationEventRunner().run(event)

    assert [item.event_type for item in state.events] == [
        EvaluationEventType.REQUESTED,
        EvaluationEventType.RUNNING,
        EvaluationEventType.GATE_DECISION,
        EvaluationEventType.CHAMPION_PROMOTED,
    ]
    assert state.champion_run_id == "run-1"


def test_event_workflow_rejects_and_alerts_on_gate_failure() -> None:
    result = evaluate_task.run(
        {
            "job_id": "job-2",
            "run_id": "run-2",
            "candidate_metrics": {"overall_f1": 0.70, "overall_accuracy": 0.70},
            "champion_metrics": {"overall_f1": 0.90, "overall_accuracy": 0.90},
        }
    )

    assert result["events"] == [
        "evaluation_requested",
        "evaluation_running",
        "gate_decision",
        "champion_rejected",
        "alert_triggered",
    ]
    assert result["alert_triggered"] is True
