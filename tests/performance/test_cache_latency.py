from __future__ import annotations

import pytest

from ares.cache.client import CacheClient


@pytest.mark.performance
def test_cache_key_value_latency(benchmark: pytest.FixtureRequest) -> None:
    async def roundtrip() -> str | None:
        client = CacheClient()
        await client.set("benchmark", "ok")
        return await client.get("benchmark")

    result = benchmark.pedantic(lambda: __import__("asyncio").run(roundtrip()), rounds=5)
    assert result == "ok"
