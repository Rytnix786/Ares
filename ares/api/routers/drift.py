from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.api.schemas.drift import (
    DriftJobCreateRequest,
    DriftJobResponse,
    DriftJobRunResponse,
    DriftPredictionIngestRequest,
    DriftPredictionIngestResponse,
    DriftReportIn,
    DriftReportResponse,
)
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.drift.contracts import ingest_prediction_payload
from ares.drift.runner import run_drift_job
from ares.models import DriftJob, DriftJobRun, DriftReportRecord

router = APIRouter(prefix="/api/v1/drift", tags=["drift"])


def _report_response(report: DriftReportRecord) -> DriftReportResponse:
    return DriftReportResponse(
        id=report.id,
        model_name=report.model_name,
        feature=report.feature,
        kl_divergence=report.kl_divergence,
        psi=report.psi,
        is_alerting=report.is_alerting,
        severity=report.severity,
        payload=report.payload,
        created_at=report.created_at.isoformat(),
        job_id=report.job_id,
        run_id=report.run_id,
    )


def _job_response(job: DriftJob) -> DriftJobResponse:
    return DriftJobResponse(
        id=job.id,
        model_name=job.model_name,
        job_name=job.job_name,
        schedule=job.schedule,
        source_type=job.source_type,
        source_config=job.source_config,
        reference_config=job.reference_config,
        thresholds=job.thresholds,
        status=job.status,
        created_by=job.created_by,
        created_at=job.created_at.isoformat(),
        updated_at=None if job.updated_at is None else job.updated_at.isoformat(),
        last_run_at=None if job.last_run_at is None else job.last_run_at.isoformat(),
        next_run_at=None if job.next_run_at is None else job.next_run_at.isoformat(),
    )


def _run_response(run: DriftJobRun) -> DriftJobRunResponse:
    return DriftJobRunResponse(
        id=run.id,
        job_id=run.job_id,
        model_name=run.model_name,
        status=run.status,
        started_at=None if run.started_at is None else run.started_at.isoformat(),
        completed_at=None if run.completed_at is None else run.completed_at.isoformat(),
        duration_seconds=run.duration_seconds,
        features_evaluated=run.features_evaluated,
        alerts_triggered=run.alerts_triggered,
        max_severity=run.max_severity,
        error_message=run.error_message,
        run_metadata=run.run_metadata,
        created_at=run.created_at.isoformat(),
    )


@router.post("/reports", response_model=DriftReportResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def create_report(
    request: Request,
    payload: DriftReportIn,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> DriftReportResponse:
    del request, _principal
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        report = await crud.create_drift_report(db, **payload.model_dump())
    return _report_response(report)


@router.get("/reports", response_model=list[DriftReportResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_reports(
    request: Request,
    model_name: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[DriftReportResponse]:
    del request, _principal
    reports = await crud.list_drift_reports(db, model_name=model_name, limit=limit)
    return [_report_response(report) for report in reports]


@router.post("/predictions", response_model=DriftPredictionIngestResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def ingest_predictions(
    request: Request,
    payload: DriftPredictionIngestRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> DriftPredictionIngestResponse:
    del request, _principal
    batch = await ingest_prediction_payload(db, model_name=payload.model_name, records=payload.records, source=payload.source)
    return DriftPredictionIngestResponse(model_name=batch.model_name, rows=batch.rows, columns=batch.columns, source=batch.source_type)


@router.post("/predictions/push", response_model=DriftPredictionIngestResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def ingest_predictions_push(
    request: Request,
    payload: DriftPredictionIngestRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> DriftPredictionIngestResponse:
    del request, _principal
    batch = await ingest_prediction_payload(db, model_name=payload.model_name, records=payload.records, source="http_push")
    return DriftPredictionIngestResponse(model_name=batch.model_name, rows=batch.rows, columns=batch.columns, source=batch.source_type)


@router.post("/jobs", response_model=DriftJobResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def create_job(
    request: Request,
    payload: DriftJobCreateRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> DriftJobResponse:
    del request, _principal
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        job = await crud.create_drift_job(db, **payload.model_dump())
    return _job_response(job)


@router.get("/jobs", response_model=list[DriftJobResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_jobs(
    request: Request,
    model_name: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[DriftJobResponse]:
    del request, _principal
    return [_job_response(job) for job in await crud.list_drift_jobs(db, model_name=model_name, status=status, limit=limit)]


@router.post("/jobs/{job_id}/run", response_model=DriftJobRunResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def run_job_now(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> DriftJobRunResponse:
    del request, _principal
    job = await crud.get_drift_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Drift job not found")
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        summary = await run_drift_job(db, job)
    runs = await crud.list_drift_job_runs(db, job_id=summary.job_id, limit=1)
    return _run_response(runs[0])


@router.get("/jobs/{job_id}/runs", response_model=list[DriftJobRunResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_job_runs(
    request: Request,
    job_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[DriftJobRunResponse]:
    del request, _principal
    return [_run_response(run) for run in await crud.list_drift_job_runs(db, job_id=job_id, limit=limit)]
