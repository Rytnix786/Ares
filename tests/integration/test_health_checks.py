"""Integration tests for health checks."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_health_live(api_client: AsyncClient):
    """Test live health check."""
    response = await api_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.integration
async def test_health_ready(api_client: AsyncClient):
    """Test ready health check with DB connectivity."""
    response = await api_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["db"] == "connected"
