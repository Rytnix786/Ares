from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_api_key
from ares.api.limiting import limiter
from ares.api.schemas.drift import DriftReportIn, DriftReportResponse
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db

router = APIRouter(prefix="/api/v1/drift", tags=["drift"], dependencies=[Depends(require_api_key)])


@router.post("/reports", response_model=DriftReportResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def create_report(request: Request, payload: DriftReportIn, db: AsyncSession = Depends(get_db)) -> DriftReportResponse:
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        report = await crud.create_drift_report(db, **payload.model_dump())
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
    )


@router.get("/reports", response_model=list[DriftReportResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_reports(request: Request, model_name: str | None = None, db: AsyncSession = Depends(get_db)) -> list[DriftReportResponse]:
    reports = await crud.list_drift_reports(db, model_name=model_name)
    return [
        DriftReportResponse(
            id=report.id,
            model_name=report.model_name,
            feature=report.feature,
            kl_divergence=report.kl_divergence,
            psi=report.psi,
            is_alerting=report.is_alerting,
            severity=report.severity,
            payload=report.payload,
            created_at=report.created_at.isoformat(),
        )
        for report in reports
    ]