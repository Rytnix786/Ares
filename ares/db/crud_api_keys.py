from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.models.api_key import ApiKey


async def create_api_key(db: AsyncSession, **values: Any) -> ApiKey:
    key = ApiKey(**values)
    db.add(key)
    await db.flush()
    await db.refresh(key)
    return key


async def get_active_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))
    return result.scalar_one_or_none()


async def list_api_keys(db: AsyncSession) -> list[ApiKey]:
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    return list(result.scalars().all())


async def revoke_api_key(db: AsyncSession, key_id: str) -> bool:
    key = await db.get(ApiKey, key_id)
    if key is None:
        return False
    key.is_active = False
    key.revoked_at = datetime.utcnow()
    await db.flush()
    return True
