from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ares.gate.rules_engine import evaluate


class EvaluationEventType(StrEnum):
    REQUESTED = "evaluation_requested"
    RUNNING = "evaluation_running"
    GATE_DECISION = "gate_decision"
    CHAMPION_PROMOTED = "champion_promoted"
    CHAMPION_REJECTED = "champion_rejected"
    ALERT_TRIGGERED = "alert_triggered"


@dataclass(frozen=True)
class EvaluationEvent:
    job_id: str
    event_type: EvaluationEventType
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationWorkflowState:
    job_id: str
    events: list[EvaluationEvent] = field(default_factory=list)
    status: str = "requested"
    champion_run_id: str | None = None
    alert_triggered: bool = False

    def append(self, event_type: EvaluationEventType, payload: dict[str, Any] | None = None) -> None:
        self.events.append(EvaluationEvent(self.job_id, event_type, payload or {}))
        self.status = event_type.value


class EvaluationEventRunner:
    def run(self, requested: EvaluationEvent) -> EvaluationWorkflowState:
        state = EvaluationWorkflowState(job_id=requested.job_id, events=[requested])
        payload = requested.payload
        state.append(EvaluationEventType.RUNNING, {"model_name": payload.get("model_name")})
        decision = evaluate(
            payload.get("candidate_metrics", {}),
            payload.get("champion_metrics", {}),
            payload.get("slice_metrics", {}),
            payload.get("gate_config", {}),
            int(payload.get("n_samples", 1)),
        )
        state.append(EvaluationEventType.GATE_DECISION, {"verdict": decision.verdict, "reason": decision.reason})
        if decision.should_promote:
            run_id = str(payload.get("run_id", requested.job_id))
            state.champion_run_id = run_id
            state.append(EvaluationEventType.CHAMPION_PROMOTED, {"run_id": run_id})
        else:
            state.append(EvaluationEventType.CHAMPION_REJECTED, {"reason": decision.reason})
            state.alert_triggered = True
            state.append(EvaluationEventType.ALERT_TRIGGERED, {"reason": decision.reason, "severity": "high"})
        return state


def build_evaluation_requested_event(job_id: str, **payload: Any) -> EvaluationEvent:
    return EvaluationEvent(job_id=job_id, event_type=EvaluationEventType.REQUESTED, payload=payload)
