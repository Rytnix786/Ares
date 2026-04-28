from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_api_key
from ares.api.limiting import limiter
from ares.api.presenters import (
    build_run_decision_payload,
    extract_metrics,
    extract_slice_regressions,
)
from ares.api.schemas.evaluation import CompareRequest, ComparisonResponse, EvaluationRunResponse
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.gate import rules_engine

router = APIRouter(prefix="/api/v1", tags=["evaluations"], dependencies=[Depends(require_api_key)])


async def _serialize_run(db: AsyncSession, run: Any) -> EvaluationRunResponse:
    active_champion = await crud.get_active_champion(db, run.model_name)
    comparison_run = None
    if active_champion is not None:
        comparison_champion = active_champion
        if active_champion.champion_run_id == run.id:
            previous = await crud.get_previous_champion(db, run.model_name)
            comparison_champion = previous
        if comparison_champion is not None:
            comparison_run = await crud.get_evaluation_run(db, comparison_champion.champion_run_id)

    comparison_payload = build_run_decision_payload(
        candidate_metrics=extract_metrics(run),
        champion_metrics=extract_metrics(comparison_run),
        candidate_slices=run.slice_metrics,
        champion_slices=None if comparison_run is None else comparison_run.slice_metrics,
        verdict="PASS" if run.passed else "FAIL",
        failure_reason=run.failure_reason,
        config_snapshot=run.gate_config_snapshot or {},
        slice_regressions=extract_slice_regressions(run.slice_metrics, run.gate_config_snapshot or {}),
    )

    return EvaluationRunResponse(
        id=run.id,
        commit_sha=run.commit_sha,
        model_name=run.model_name,
        model_version=run.model_version,
        passed=run.passed,
        overall_f1=run.overall_f1,
        overall_accuracy=run.overall_accuracy,
        overall_precision=run.overall_precision,
        overall_recall=run.overall_recall,
        latency_p50_ms=run.latency_p50_ms,
        latency_p99_ms=run.latency_p99_ms,
        duration_seconds=run.duration_seconds,
        failure_reason=run.failure_reason,
        golden_set_version=run.golden_set_version,
        mlflow_run_id=run.mlflow_run_id,
        artifact_uri=run.artifact_uri,
        slice_metrics=run.slice_metrics or {},
        gate_config_snapshot=run.gate_config_snapshot or {},
        metadata_json=run.metadata_json or {},
        champion_run_id=None if active_champion is None else active_champion.champion_run_id,
        is_current_champion=bool(active_champion is not None and active_champion.champion_run_id == run.id),
        created_at=run.created_at.isoformat(),
        **comparison_payload,
    )


@router.post("/evaluate/compare", response_model=ComparisonResponse)
@limiter.limit(settings.RATE_LIMIT_EVALUATE)
async def compare_with_champion(request: Request, payload: CompareRequest, db: AsyncSession = Depends(get_db)) -> ComparisonResponse:
    del request
    champion = await crud.get_active_champion(db, payload.model_name)
    gate_config = rules_engine.snapshot_gate_config()
    baseline_slice_regressions = extract_slice_regressions(payload.slice_metrics, gate_config)
    if champion is None:
        comparison_payload = build_run_decision_payload(
            candidate_metrics=payload.new_metrics,
            champion_metrics={},
            candidate_slices=payload.slice_metrics,
            champion_slices=None,
            verdict="PASS",
            failure_reason=None,
            config_snapshot=gate_config,
            slice_regressions=baseline_slice_regressions,
        )
        return ComparisonResponse(
            decision="PASS",
            reason="No champion exists. This run becomes the baseline.",
            new_metrics=payload.new_metrics,
            slice_regressions=baseline_slice_regressions,
            config_snapshot=gate_config,
            is_first_run=True,
            should_promote=True,
            **comparison_payload,
        )
    champion_run = await crud.get_evaluation_run(db, champion.champion_run_id)
    champion_metrics = extract_metrics(champion_run)
    decision = rules_engine.evaluate(payload.new_metrics, champion_metrics, payload.slice_metrics, gate_config, payload.n_samples)
    comparison_payload = build_run_decision_payload(
        candidate_metrics=payload.new_metrics,
        champion_metrics=champion_metrics,
        candidate_slices=payload.slice_metrics,
        champion_slices=None if champion_run is None else champion_run.slice_metrics,
        verdict=decision.verdict,
        failure_reason=decision.reason,
        config_snapshot=gate_config,
        slice_regressions=decision.slice_regressions,
    )
    return ComparisonResponse(
        decision=decision.verdict,
        reason=decision.reason,
        new_metrics=payload.new_metrics,
        slice_regressions=decision.slice_regressions,
        config_snapshot=gate_config,
        should_promote=decision.should_promote,
        **comparison_payload,
    )


@router.get("/evaluations/", response_model=list[EvaluationRunResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_runs(request: Request, db: AsyncSession = Depends(get_db)) -> list[EvaluationRunResponse]:
    del request
    runs = await crud.list_evaluation_runs(db)
    return [await _serialize_run(db, run) for run in runs]


@router.get("/evaluations/{run_id}", response_model=EvaluationRunResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_run(request: Request, run_id: str, db: AsyncSession = Depends(get_db)) -> EvaluationRunResponse:
    del request
    run = await crud.get_evaluation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return await _serialize_run(db, run)