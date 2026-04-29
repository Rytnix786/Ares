from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.models.webhook import Webhook


async def create_webhook(db: AsyncSession, **values: Any) -> Webhook:
    webhook = Webhook(**values)
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def list_active_webhooks(db: AsyncSession, event_type: str | None = None) -> list[Webhook]:
    stmt = select(Webhook).where(Webhook.is_active.is_(True))
    if event_type:
        stmt = stmt.where(Webhook.event_type == event_type)
    result = await db.execute(stmt.order_by(Webhook.created_at.desc()))
    return list(result.scalars().all())
