"""Database connection pool health monitoring."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

log = logging.getLogger(__name__)


class PoolHealthMonitor:
    """Monitor and report on database connection pool health."""
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
    
    def get_pool_status(self) -> dict[str, Any]:
        """Get current pool status."""
        if self.engine is None or self.engine.pool is None:
            return {
                "pool_type": "not_initialized",
                "pool_size": 0,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "max_overflow": 0,
            }
        
        pool = self.engine.pool
        # Handle StaticPool (used for SQLite in-memory)
        if hasattr(pool, "size"):
            checked_in = getattr(pool, "checkedin", lambda: 0)()
            checked_out = getattr(pool, "checkedout", lambda: 0)()
            overflow = getattr(pool, "overflow", lambda: 0)()
            return {
                "pool_size": pool.size(),
                "checked_in": checked_in,
                "checked_out": checked_out,
                "overflow": overflow,
                "max_overflow": pool._max_overflow if hasattr(pool, "_max_overflow") else 0,
            }
        else:
            # StaticPool doesn't have pool metrics
            return {
                "pool_type": "static",
                "pool_size": 1,
                "checked_in": 0,
                "checked_out": 0,
                "overflow": 0,
                "max_overflow": 0,
            }
    
    def is_healthy(self) -> bool:
        """Check if pool is healthy."""
        status = self.get_pool_status()
        # Pool is healthy if it's not at max capacity with all connections checked out
        max_capacity = status["pool_size"] + status["max_overflow"]
        return bool(status["checked_out"] < max_capacity)
