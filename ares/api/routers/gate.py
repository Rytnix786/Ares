from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.api.presenters import (
    build_run_decision_payload,
    extract_metrics,
    extract_slice_regressions,
)
from ares.api.schemas.evaluation import SimulationRequest, SimulationResponse
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.gate.rules_engine import evaluate, snapshot_gate_config

router = APIRouter(prefix="/api/v1/gate", tags=["gate"])


@router.get("/config")
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_gate_config(
    request: Request,
    _principal: object = Depends(require_scope("read")),
) -> dict[str, object]:
    del request
    return snapshot_gate_config()


@router.post("/simulate", response_model=SimulationResponse)
@limiter.limit(settings.RATE_LIMIT_EVALUATE)
async def simulate_gate(
    request: Request,
    payload: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> SimulationResponse:
    del request
    run = await crud.get_evaluation_run(db, payload.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")

    gate_config = snapshot_gate_config()
    gate_config.update(payload.override_thresholds)

    active_champion = await crud.get_active_champion(db, run.model_name)
    comparison_run = None
    if active_champion is not None:
        comparison_champion = active_champion
        if active_champion.champion_run_id == run.id:
            comparison_champion = await crud.get_previous_champion(db, run.model_name)
        if comparison_champion is not None:
            comparison_run = await crud.get_evaluation_run(db, comparison_champion.champion_run_id)

    candidate_metrics = extract_metrics(run)
    champion_metrics = extract_metrics(comparison_run)
    slice_regressions = extract_slice_regressions(run.slice_metrics, gate_config)

    if champion_metrics:
        decision = evaluate(candidate_metrics, champion_metrics, run.slice_metrics, gate_config, run.n_samples_evaluated)
        verdict = decision.verdict
        reason = decision.reason
        should_promote = decision.should_promote
        slice_regressions = decision.slice_regressions
    else:
        verdict = "PASS"
        reason = "No champion exists. This run becomes the baseline."
        should_promote = True

    comparison_payload = build_run_decision_payload(
        candidate_metrics=candidate_metrics,
        champion_metrics=champion_metrics,
        candidate_slices=run.slice_metrics,
        champion_slices=None if comparison_run is None else comparison_run.slice_metrics,
        verdict=verdict,
        failure_reason=reason if verdict == "FAIL" else None,
        config_snapshot=gate_config,
        slice_regressions=slice_regressions,
    )
    return SimulationResponse(
        run_id=run.id,
        decision=verdict,
        reason=reason,
        slice_regressions=slice_regressions,
        config_snapshot=gate_config,
        should_promote=should_promote,
        is_first_run=not champion_metrics,
        new_metrics=candidate_metrics,
        **comparison_payload,
    )