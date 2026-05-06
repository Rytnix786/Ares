from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.api.presenters import (
    build_run_decision_payload,
    extract_metrics,
    extract_slice_regressions,
)
from ares.api.schemas.evaluation import (
    CompareRequest,
    ComparisonResponse,
    EvaluationRunResponse,
    EvaluatorPluginResponse,
    ModelCardResponse,
    MultiModelCompareRequest,
    MultiModelCompareResponse,
    MultiModelCompareRow,
    SliceTrendPointResponse,
    SliceTrendRetentionResponse,
)
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.gate import rules_engine
from ares.gate.plugins import evaluate_with_plugin
from ares.model_cards import generate_model_card
from ares.plugins import list_evaluator_plugins

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


@router.get("/evaluators", response_model=list[EvaluatorPluginResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def evaluators(request: Request, _principal: object = Depends(require_scope("read"))) -> list[EvaluatorPluginResponse]:
    del request, _principal
    return [EvaluatorPluginResponse(name=p.name, version=p.version, description=p.description) for p in list_evaluator_plugins()]


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
        model_card_uri=run.model_card_uri,
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
async def compare_with_champion(
    request: Request,
    payload: CompareRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> ComparisonResponse:
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
    decision = evaluate_with_plugin("default", payload.new_metrics, champion_metrics, payload.slice_metrics, gate_config, payload.n_samples)
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
async def list_runs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[EvaluationRunResponse]:
    del request
    runs = await crud.list_evaluation_runs(db)
    return [await _serialize_run(db, run) for run in runs]


@router.post("/evaluations/compare", response_model=MultiModelCompareResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def compare_many(
    request: Request,
    payload: MultiModelCompareRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> MultiModelCompareResponse:
    del request, _principal
    rows: list[MultiModelCompareRow] = []
    for run_id in payload.run_ids:
        run = await crud.get_evaluation_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Evaluation run not found: {run_id}")
        metrics = extract_metrics(run)
        rows.append(MultiModelCompareRow(run_id=run.id, model_name=run.model_name, model_version=run.model_version, passed=run.passed, metrics=metrics, risk_summary="passed" if run.passed else (run.failure_reason or "failed")))
    eligible = [row for row in rows if row.passed]
    winner = max(eligible or rows, key=lambda row: row.metrics.get("overall_f1", row.metrics.get("overall_accuracy", 0.0)))
    rankings = [
        {
            "rank": rank,
            "run_id": row.run_id,
            "model_name": row.model_name,
            "model_version": row.model_version,
            "passed": row.passed,
            "overall_f1": row.metrics.get("overall_f1"),
            "overall_accuracy": row.metrics.get("overall_accuracy"),
            "risk_summary": row.risk_summary,
        }
        for rank, row in enumerate(
            sorted(rows, key=lambda item: item.metrics.get("overall_f1", item.metrics.get("overall_accuracy", 0.0)), reverse=True),
            start=1,
        )
    ]
    failed_count = sum(1 for row in rows if not row.passed)
    risk_level = "high" if failed_count == len(rows) else "medium" if failed_count else "low"
    return MultiModelCompareResponse(
        candidates=rows,
        winner_run_id=winner.run_id,
        winner_reason="highest passing overall_f1/accuracy",
        winner={"run_id": winner.run_id, "model_name": winner.model_name, "model_version": winner.model_version},
        risk_summary={"level": risk_level, "failed_candidates": failed_count, "compared_candidates": len(rows)},
        rankings=rankings,
    )


@router.get("/evaluations/{run_id}", response_model=EvaluationRunResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_run(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> EvaluationRunResponse:
    del request
    run = await crud.get_evaluation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return await _serialize_run(db, run)


@router.get("/slices/trends", response_model=list[SliceTrendPointResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def slice_trends(
    request: Request,
    model_name: str | None = None,
    slice_name: str | None = None,
    metric_name: str | None = None,
    limit: int = 500,
    alert_threshold: float | None = None,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[SliceTrendPointResponse]:
    del request, _principal
    points = await crud.list_slice_metric_trends(db, model_name=model_name, slice_name=slice_name, metric_name=metric_name, limit=limit)
    if alert_threshold is not None:
        for point in points:
            if point.is_critical and point.metric_value < alert_threshold:
                await crud.create_alert_event(
                    db,
                    event_type="slice_trend_threshold_breach",
                    source="slice_trends_api",
                    model_name=point.model_name,
                    severity="warning",
                    status="open",
                    dedupe_key=f"slice-trend:{point.model_name}:{point.slice_name}:{point.metric_name}",
                    message=f"Critical slice {point.slice_name}.{point.metric_name} below threshold",
                    payload={"run_id": point.run_id, "value": point.metric_value, "threshold": alert_threshold},
                )
    return [SliceTrendPointResponse(run_id=p.run_id, model_name=p.model_name, slice_name=p.slice_name, metric_name=p.metric_name, metric_value=p.metric_value, is_critical=p.is_critical, created_at=p.created_at.isoformat()) for p in points]


@router.delete("/slices/trends/retention", response_model=SliceTrendRetentionResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def purge_slice_trends(
    request: Request,
    retention_days: int = settings.SLICE_TREND_RETENTION_DAYS,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> SliceTrendRetentionResponse:
    del request, _principal
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        deleted = await crud.purge_slice_metric_points(db, older_than=cutoff)
    return SliceTrendRetentionResponse(deleted=deleted, retention_days=retention_days)


@router.get("/evaluations/{run_id}/model-card", response_model=ModelCardResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def model_card(
    request: Request,
    run_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> ModelCardResponse:
    del request, _principal
    run = await crud.get_evaluation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    champion = await crud.get_active_champion(db, run.model_name)
    card = generate_model_card(
        run,
        champion=champion,
        drift_reports=await crud.list_drift_reports(db, model_name=run.model_name, limit=20),
        champion_history=await crud.list_champion_history(db, run.model_name),
    )
    if run.model_card_uri is None:
        await crud.attach_model_card(db, run.id, markdown_uri=f"ares://model-cards/{run.id}.md", payload=card.payload)
    return ModelCardResponse(run_id=run.id, markdown=card.markdown, payload=card.payload)
