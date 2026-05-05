from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import hash_api_key, require_scope
from ares.api.limiting import limiter
from ares.api.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyRevokeRequest,
    ApiKeyRotateRequest,
)
from ares.config import settings
from ares.db.crud_api_keys import create_api_key, list_api_keys, revoke_api_key, rotate_api_key
from ares.db.session import get_db

router = APIRouter(prefix="/api/v1/admin/api-keys", tags=["admin-api-keys"])


def _expires(ttl_days: int | None) -> datetime | None:
    return datetime.utcnow() + timedelta(days=ttl_days) if ttl_days else None


def _response(key: Any) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=key.id,
        name=key.name,
        scopes=list(key.scopes or []),
        rate_limit=key.rate_limit,
        is_active=key.is_active,
        created_at=key.created_at,
        revoked_at=key.revoked_at,
        expires_at=key.expires_at,
        last_used_at=key.last_used_at,
        use_count=key.use_count,
        revoked_by=key.revoked_by,
        revocation_reason=key.revocation_reason,
        rotated_from_key_id=key.rotated_from_key_id,
        rotated_to_key_id=key.rotated_to_key_id,
        rotation_grace_expires_at=key.rotation_grace_expires_at,
    )


@router.post("", response_model=ApiKeyCreateResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def create_key(
    request: Request,
    payload: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> ApiKeyCreateResponse:
    del request, _principal
    raw_key = payload.key or f"ares_{secrets.token_urlsafe(32)}"
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        key = await create_api_key(
            db,
            key_hash=hash_api_key(raw_key),
            name=payload.name,
            scopes=payload.scopes,
            rate_limit=payload.rate_limit or settings.API_KEY_DEFAULT_RATE_LIMIT,
            expires_at=_expires(payload.ttl_days),
            api_metadata=payload.metadata,
        )
    return ApiKeyCreateResponse(key=raw_key, record=_response(key))


@router.get("", response_model=list[ApiKeyResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def list_keys(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> list[ApiKeyResponse]:
    del request, _principal
    return [_response(key) for key in await list_api_keys(db)]


@router.post("/{key_id}/rotate", response_model=ApiKeyCreateResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def rotate_key(
    request: Request,
    key_id: str,
    payload: ApiKeyRotateRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> ApiKeyCreateResponse:
    del request, _principal
    raw_key = payload.key or f"ares_{secrets.token_urlsafe(32)}"
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        key = await rotate_api_key(
            db,
            key_id,
            new_key_hash=hash_api_key(raw_key),
            name=payload.name,
            scopes=payload.scopes,
            rate_limit=payload.rate_limit,
            expires_at=_expires(payload.ttl_days),
            grace_days=payload.grace_days,
        )
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return ApiKeyCreateResponse(key=raw_key, record=_response(key))


@router.post("/{key_id}/revoke", response_model=dict[str, bool])
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def revoke_key(
    request: Request,
    key_id: str,
    payload: ApiKeyRevokeRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> dict[str, bool]:
    del request, _principal
    async with (db.begin_nested() if db.in_transaction() else db.begin()):
        revoked = await revoke_api_key(db, key_id, revoked_by=payload.revoked_by, reason=payload.reason)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": True}
