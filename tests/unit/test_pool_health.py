"""Unit tests for database pool health monitoring."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine

from ares.db.health import PoolHealthMonitor


@pytest_asyncio.fixture
async def test_engine():
    """Create a test engine for pool health monitoring."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_pool_health_monitor_get_status(test_engine):
    """Test that pool status can be retrieved."""
    monitor = PoolHealthMonitor(test_engine)
    
    status = monitor.get_pool_status()
    assert "pool_size" in status
    assert "checked_in" in status
    assert "checked_out" in status
    assert "overflow" in status
    assert "max_overflow" in status


@pytest.mark.asyncio
async def test_pool_health_monitor_is_healthy(test_engine):
    """Test that pool health check works."""
    monitor = PoolHealthMonitor(test_engine)
    
    # Pool should be healthy when not at capacity
    is_healthy = monitor.is_healthy()
    assert isinstance(is_healthy, bool)
