from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.models.api_key import ApiKey


async def create_api_key(db: AsyncSession, **values: Any) -> ApiKey:
    key = ApiKey(**values)
    db.add(key)
    await db.flush()
    await db.refresh(key)
    return key


async def get_active_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    now = datetime.utcnow()
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
            or_(ApiKey.expires_at.is_(None), ApiKey.expires_at > now),
            or_(ApiKey.rotation_grace_expires_at.is_(None), ApiKey.rotation_grace_expires_at > now),
        )
    )
    return result.scalar_one_or_none()


async def record_api_key_usage(db: AsyncSession, key_id: str, *, used_at: datetime | None = None) -> None:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return
    key.last_used_at = used_at or datetime.utcnow()
    key.use_count = int(key.use_count or 0) + 1
    key.updated_at = datetime.utcnow()
    await db.flush()


async def list_api_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str, *, revoked_by: str | None = None, reason: str | None = None) -> bool:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return False
    key.is_active = False
    key.revoked_at = datetime.utcnow()
    key.revoked_by = revoked_by
    key.revocation_reason = reason
    key.updated_at = datetime.utcnow()
    await db.flush()
    return True


async def rotate_api_key(
    db: AsyncSession,
    old_key_id: str,
    *,
    new_key_hash: str,
    name: str | None = None,
    scopes: list[str] | None = None,
    rate_limit: str | None = None,
    expires_at: datetime | None = None,
    grace_days: int = 0,
) -> ApiKey | None:
    old_key = await db.get(ApiKey, old_key_id)
    if old_key is None:
        return None
    now = datetime.utcnow()
    new_key = ApiKey(
        key_hash=new_key_hash,
        name=name or f"{old_key.name}-rotated",
        scopes=scopes if scopes is not None else list(old_key.scopes or []),
        rate_limit=rate_limit if rate_limit is not None else old_key.rate_limit,
        expires_at=expires_at,
        rotated_from_key_id=old_key.id,
    )
    db.add(new_key)
    await db.flush()
    old_key.rotated_to_key_id = new_key.id
    old_key.updated_at = now
    if grace_days <= 0:
        old_key.is_active = False
        old_key.revoked_at = now
        old_key.revocation_reason = "rotated"
    else:
        old_key.rotation_grace_expires_at = now + timedelta(days=grace_days)
    await db.flush()
    await db.refresh(new_key)
    return new_key
