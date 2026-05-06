from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ares.config import settings
from ares.db import crud

logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    def __init__(self, session_factory: Any | None = None) -> None:
        self.session_factory = session_factory
        self.logger = logger

    async def purge_audit_logs(self, db_session: AsyncSession, retention_days: int | None = None) -> dict[str, int]:
        effective_retention = retention_days or settings.AUDIT_LOG_RETENTION_DAYS
        cutoff = datetime.utcnow() - timedelta(days=effective_retention)
        deleted = await crud.purge_audit_logs(db_session, older_than=cutoff)
        self.logger.info("Purged %s audit log entries older than %s days", deleted, effective_retention)
        return {"deleted": deleted, "retention_days": effective_retention}