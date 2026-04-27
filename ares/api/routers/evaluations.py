from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_api_key
from ares.api.limiting import limiter
from ares.api.schemas.evaluation import CompareRequest, ComparisonResponse, EvaluationRunResponse
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.gate import rules_engine

router = APIRouter(prefix="/api/v1", tags=["evaluations"], dependencies=[Depends(require_api_key)])


@router.post("/evaluate/compare", response_model=ComparisonResponse)
@limiter.limit(settings.RATE_LIMIT_EVALUATE)
async def compare_with_champion(request: Request, payload: CompareRequest, db: AsyncSession = Depends(get_db)) -> ComparisonResponse:
    champion = await crud.get_active_champion(db, payload.model_name)
    if champion is None:
        return ComparisonResponse(decision="PASS", reason="No champion exists. This run becomes the baseline.", new_metrics=payload.new_metrics, is_first_run=True, should_promote=True)
    champion_run = await crud.get_evaluation_run(db, champion.champion_run_id)
    champion_metrics = {} if champion_run is None else {"overall_f1": champion_run.overall_f1, "overall_accuracy": champion_run.overall_accuracy, "latency_p99_ms": champion_run.latency_p99_ms, "model_size_mb": champion_run.model_size_mb}
    decision = rules_engine.evaluate(payload.new_metrics, champion_metrics, payload.slice_metrics, n_samples=payload.n_samples)
    return ComparisonResponse(decision=decision.verdict, reason=decision.reason, delta_metrics=decision.deltas, champion_metrics=champion_metrics, new_metrics=payload.new_metrics, slice_regressions=decision.slice_regressions, should_promote=decision.should_promote)


@router.get("/evaluations/", response_model=list[EvaluationRunResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_runs(request: Request, db: AsyncSession = Depends(get_db)) -> list[EvaluationRunResponse]:
    runs = await crud.list_evaluation_runs(db)
    return [
        EvaluationRunResponse(
            id=r.id,
            commit_sha=r.commit_sha,
            model_name=r.model_name,
            model_version=r.model_version,
            passed=r.passed,
            overall_f1=r.overall_f1,
            overall_accuracy=r.overall_accuracy,
            overall_precision=r.overall_precision,
            overall_recall=r.overall_recall,
            latency_p50_ms=r.latency_p50_ms,
            latency_p99_ms=r.latency_p99_ms,
            duration_seconds=r.duration_seconds,
            failure_reason=r.failure_reason,
            golden_set_version=r.golden_set_version,
            mlflow_run_id=r.mlflow_run_id,
            artifact_uri=r.artifact_uri,
            created_at=r.created_at.isoformat(),
        )
        for r in runs
    ]


@router.get("/evaluations/{run_id}", response_model=EvaluationRunResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_run(request: Request, run_id: str, db: AsyncSession = Depends(get_db)) -> EvaluationRunResponse:
    run = await crud.get_evaluation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
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
        created_at=run.created_at.isoformat(),
    )