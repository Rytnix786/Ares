from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ares.api.auth import require_api_key
from ares.api.limiting import limiter
from ares.config import settings
from ares.gate.rules_engine import snapshot_gate_config

router = APIRouter(prefix="/api/v1/gate", tags=["gate"], dependencies=[Depends(require_api_key)])


@router.get("/config")
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_gate_config(request: Request) -> dict[str, object]:
    del request
    return snapshot_gate_config()