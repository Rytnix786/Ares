from __future__ import annotations

import pytest

from ares.api.auth import hash_api_key
from ares.db.crud_api_keys import create_api_key, get_active_api_key_by_hash, revoke_api_key


def test_hash_api_key_is_stable() -> None:
    assert hash_api_key("secret") == hash_api_key("secret")
    assert hash_api_key("secret") != hash_api_key("other")


@pytest.mark.asyncio
async def test_api_key_crud_lifecycle(async_session) -> None:
    digest = hash_api_key("unit-test-key")
    key = await create_api_key(
        async_session,
        key_hash=digest,
        name="unit",
        scopes=["read"],
        is_active=True,
    )
    assert await get_active_api_key_by_hash(async_session, digest) == key
    assert await revoke_api_key(async_session, key.id) is True
    assert await get_active_api_key_by_hash(async_session, digest) is None
