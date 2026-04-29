from __future__ import annotations

import os
import shutil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ares.db.health import PoolHealthMonitor
from ares.db.session import engine, get_db

router = APIRouter(tags=["health"])

def get_pool_monitor() -> PoolHealthMonitor:
    """Get pool monitor instance."""
    return PoolHealthMonitor(engine)

@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}

@router.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # Check DB connectivity
    try:
        await db.execute(text("select 1"))
        db_status = "connected"
    except Exception as exc:
        db_status = "disconnected"
        raise HTTPException(status_code=503, detail="Database not ready") from exc
    
    # Check Redis connectivity (if configured)
    redis_status = "not_configured"
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as redis
            redis_client = redis.from_url(redis_url)
            await redis_client.ping()
            await redis_client.close()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
    
    # Check MinIO connectivity (if configured)
    minio_status = "not_configured"
    minio_endpoint = os.environ.get("MINIO_ENDPOINT")
    if minio_endpoint:
        try:
            from minio import Minio
            minio_client = Minio(
                minio_endpoint,
                access_key=os.environ.get("MINIO_ACCESS_KEY", ""),
                secret_key=os.environ.get("MINIO_SECRET_KEY", ""),
                secure=False,
            )
            minio_client.list_buckets()
            minio_status = "connected"
        except Exception:
            minio_status = "disconnected"
    
    # Check disk space
    disk_status = "ok"
    disk_path = os.environ.get("DATA_PATH", ".")
    try:
        disk_usage = shutil.disk_usage(disk_path)
        disk_free_percent = (disk_usage.free / disk_usage.total) * 100
        if disk_free_percent < 10:
            disk_status = "low"
        elif disk_free_percent < 5:
            disk_status = "critical"
    except Exception:
        disk_status = "unknown"
    
    return {
        "status": "ready",
        "db": db_status,
        "redis": redis_status,
        "minio": minio_status,
        "disk": disk_status,
    }

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("select 1"))
    return {"status": "healthy", "db": "connected", "version": "1.0.0"}

@router.get("/health/pool")
async def pool_health() -> dict[str, Any]:
    """Get database connection pool health status."""
    monitor = get_pool_monitor()
    return monitor.get_pool_status()