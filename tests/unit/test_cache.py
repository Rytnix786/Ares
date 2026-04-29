from __future__ import annotations

import pytest

from ares.cache.client import CacheClient
from ares.cache.keys import cache_key


def test_cache_key_is_stable() -> None:
    assert cache_key("runs", {"b": 2, "a": 1}) == cache_key("runs", {"a": 1, "b": 2})


@pytest.mark.asyncio
async def test_cache_client_memory_json_roundtrip() -> None:
    client = CacheClient()
    await client.set_json("key", {"value": 1})
    assert await client.get_json("key") == {"value": 1}
    await client.delete("key")
    assert await client.get_json("key") is None
