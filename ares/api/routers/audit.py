from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _audit_response(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "request_id": row.request_id,
        "timestamp": row.timestamp.isoformat(),
        "user": row.user,
        "endpoint": row.endpoint,
        "method": row.method,
        "payload_hash": row.payload_hash,
        "result": row.result,
        "status_code": row.status_code,
        "audit_metadata": row.audit_metadata,
        "api_key_id": row.api_key_id,
        "actor_type": row.actor_type,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "action": row.action,
        "correlation_id": row.correlation_id,
        "error_code": row.error_code,
        "duration_ms": row.duration_ms,
    }


@router.get("/events", response_model=list[dict[str, Any]])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_events(
    request: Request,
    user: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> list[dict[str, Any]]:
    del request, _principal
    return [
        _audit_response(row)
        for row in await crud.list_audit_logs(db, user=user, action=action, resource_type=resource_type, limit=limit)
    ]


@router.delete("/events/retention", response_model=dict[str, int])
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def purge_events(
    request: Request,
    retention_days: int = 365,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> dict[str, int]:
    del request, _principal
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        deleted = await crud.purge_audit_logs(db, older_than=cutoff)
    return {"deleted": deleted}
