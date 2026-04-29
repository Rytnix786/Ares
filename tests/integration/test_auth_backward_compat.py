from __future__ import annotations

import os

import pytest


@pytest.mark.integration
async def test_env_based_api_key_still_works_after_db_migration() -> None:
    original_api_keys = os.environ.get("ARES_API_KEYS", "")
    original_env = os.environ.get("ENVIRONMENT", "")
    try:
        test_key = "test-env-key-12345"
        os.environ["ARES_API_KEYS"] = test_key
        os.environ["ENVIRONMENT"] = "testing"
        from ares.api import auth
        from ares.config import get_settings

        get_settings.cache_clear()
        auth.settings = get_settings()
        principal = await auth.require_api_key(test_key)
        assert principal.key == test_key
        assert principal.has_scope("read")
    finally:
        os.environ["ARES_API_KEYS"] = original_api_keys
        os.environ["ENVIRONMENT"] = original_env
        from ares.config import get_settings

        get_settings.cache_clear()


@pytest.mark.integration
async def test_db_key_takes_precedence_over_env_key(async_session, monkeypatch: pytest.MonkeyPatch) -> None:
    from ares.api import auth
    from ares.db.crud_api_keys import create_api_key
    test_key = "shared-test-key-67890"
    await create_api_key(
        async_session,
        key_hash=auth.hash_api_key(test_key),
        name="test-restricted-key",
        scopes=["read"],
        is_active=True,
    )
    await async_session.flush()

    class _SessionFactory:
        def __call__(self):
            return self

        async def __aenter__(self):
            return async_session

        async def __aexit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(auth, "get_sessionmaker", lambda: _SessionFactory())
    principal = await auth.require_api_key(test_key)
    assert principal.scopes == frozenset({"read"})
    assert not principal.has_scope("write")
