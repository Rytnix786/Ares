from __future__ import annotations

import json
from typing import Any

from ares.config import settings


class CacheClient:
    """Small async cache wrapper with Redis when enabled and in-memory fallback."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._memory: dict[str, str] = {}

    @classmethod
    async def create(cls) -> CacheClient:
        if not settings.CACHE_ENABLED:
            return cls()
        try:
            from redis.asyncio import Redis

            redis_client = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=settings.CACHE_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=settings.CACHE_SOCKET_TIMEOUT_SECONDS,
            )
            await redis_client.ping()
            return cls(redis_client)
        except Exception:
            return cls()

    async def get_json(self, key: str) -> Any | None:
        raw = await self.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        await self.set(key, json.dumps(value, default=str), ttl_seconds=ttl_seconds)

    async def get(self, key: str) -> str | None:
        if self._redis is not None:
            value = await self._redis.get(key)
            return None if value is None else str(value)
        return self._memory.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        ttl = settings.CACHE_TTL_SECONDS if ttl_seconds is None else ttl_seconds
        if self._redis is not None:
            await self._redis.set(key, value, ex=ttl)
            return
        self._memory[key] = value

    async def delete(self, key: str) -> None:
        if self._redis is not None:
            await self._redis.delete(key)
            return
        self._memory.pop(key, None)

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()


_cache_client: CacheClient | None = None


async def get_cache_client() -> CacheClient:
    global _cache_client
    if _cache_client is None:
        _cache_client = await CacheClient.create()
    return _cache_client
