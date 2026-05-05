from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.api.schemas.alert import AlertEventResponse, AlertStatusUpdateRequest
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.models import AlertEvent

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _response(event: AlertEvent) -> AlertEventResponse:
    return AlertEventResponse(
        id=event.id,
        event_type=event.event_type,
        source=event.source,
        model_name=event.model_name,
        severity=event.severity,
        status=event.status,
        dedupe_key=event.dedupe_key,
        drift_report_id=event.drift_report_id,
        drift_run_id=event.drift_run_id,
        evaluation_run_id=event.evaluation_run_id,
        message=event.message,
        payload=event.payload,
        created_at=event.created_at.isoformat(),
        acknowledged_at=None if event.acknowledged_at is None else event.acknowledged_at.isoformat(),
        acknowledged_by=event.acknowledged_by,
        resolved_at=None if event.resolved_at is None else event.resolved_at.isoformat(),
        resolved_by=event.resolved_by,
    )


@router.get("/events", response_model=list[AlertEventResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_events(
    request: Request,
    model_name: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[AlertEventResponse]:
    del request, _principal
    return [_response(event) for event in await crud.list_alert_events(db, model_name=model_name, status=status, limit=limit)]


@router.patch("/events/{event_id}", response_model=AlertEventResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def update_event(
    request: Request,
    event_id: str,
    payload: AlertStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> AlertEventResponse:
    del request, _principal
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        event = await crud.update_alert_event_status(db, event_id, payload.status, payload.actor)
    if event is None:
        raise HTTPException(status_code=404, detail="Alert event not found")
    return _response(event)
