from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ares.api.auth import hash_api_key
from ares.db.crud_api_keys import (
    create_api_key,
    get_active_api_key_by_hash,
    record_api_key_usage,
    revoke_api_key,
    rotate_api_key,
)


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


@pytest.mark.asyncio
async def test_api_key_expiration_and_usage_tracking(async_session) -> None:
    active_digest = hash_api_key("active-key")
    expired_digest = hash_api_key("expired-key")
    active = await create_api_key(
        async_session,
        key_hash=active_digest,
        name="active",
        scopes=["read"],
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    await create_api_key(
        async_session,
        key_hash=expired_digest,
        name="expired",
        scopes=["read"],
        is_active=True,
        expires_at=datetime.utcnow() - timedelta(seconds=1),
    )

    assert await get_active_api_key_by_hash(async_session, active_digest) == active
    assert await get_active_api_key_by_hash(async_session, expired_digest) is None

    await record_api_key_usage(async_session, active.id)
    assert active.last_used_at is not None
    assert active.use_count == 1


@pytest.mark.asyncio
async def test_api_key_rotation_links_records_and_revokes_without_grace(async_session) -> None:
    old_digest = hash_api_key("old-key")
    old = await create_api_key(
        async_session,
        key_hash=old_digest,
        name="old",
        scopes=["read", "write"],
        is_active=True,
    )

    new = await rotate_api_key(async_session, old.id, new_key_hash=hash_api_key("new-key"), grace_days=0)

    assert new is not None
    assert new.rotated_from_key_id == old.id
    assert old.rotated_to_key_id == new.id
    assert old.is_active is False
    assert await get_active_api_key_by_hash(async_session, old_digest) is None
    assert await get_active_api_key_by_hash(async_session, hash_api_key("new-key")) == new


@pytest.mark.asyncio
async def test_api_key_rotation_grace_keeps_old_key_temporarily(async_session) -> None:
    old_digest = hash_api_key("old-grace-key")
    old = await create_api_key(
        async_session,
        key_hash=old_digest,
        name="old-grace",
        scopes=["read"],
        is_active=True,
    )

    new = await rotate_api_key(async_session, old.id, new_key_hash=hash_api_key("new-grace-key"), grace_days=1)

    assert new is not None
    assert old.is_active is True
    assert old.rotation_grace_expires_at is not None
    assert await get_active_api_key_by_hash(async_session, old_digest) == old
