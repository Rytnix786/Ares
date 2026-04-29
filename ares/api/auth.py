from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status

from ares.config import settings
from ares.db.crud_api_keys import get_active_api_key_by_hash
from ares.db.session import get_sessionmaker


@dataclass(frozen=True)
class APIKeyPrincipal:
    key: str
    key_id: str
    scopes: frozenset[str]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin" in self.scopes


def rate_limit_key(request: Request) -> str:
    return request.headers.get("x-api-key") or (request.client.host if request.client else "anonymous")


def hash_api_key(api_key: str) -> str:
    return hmac.new(settings.API_KEY_HASH_SECRET.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256).hexdigest()[: settings.API_KEY_HASH_PREFIX_LENGTH]


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> APIKeyPrincipal:
    current_settings = settings
    if x_api_key:
        try:
            async with get_sessionmaker()() as session:
                db_key = await get_active_api_key_by_hash(session, hash_api_key(x_api_key))
                if db_key is not None:
                    return APIKeyPrincipal(key=x_api_key, key_id=db_key.id, scopes=frozenset(db_key.scopes or []))
        except Exception:
            # Preserve env-key compatibility if DB key infrastructure is not ready.
            pass
    if not current_settings.ARES_API_KEYS:
        if current_settings.ENVIRONMENT == "development":
            return APIKeyPrincipal(
                key="development",
                key_id="development",
                scopes=frozenset({"read", "write", "admin"}),
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API keys are not configured")
    if x_api_key:
        for allowed in current_settings.ARES_API_KEYS:
            if hmac.compare_digest(x_api_key, allowed):
                return APIKeyPrincipal(
                    key=x_api_key,
                    key_id=allowed,
                    scopes=current_settings.scopes_for_api_key(allowed),
                )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_scope(scope: str) -> Callable[[APIKeyPrincipal], APIKeyPrincipal]:
    def dependency(principal: APIKeyPrincipal = Depends(require_api_key)) -> APIKeyPrincipal:
        if principal.has_scope(scope):
            return principal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "INSUFFICIENT_SCOPE",
                "message": f"API key lacks required scope: {scope}",
                "details": {
                    "required_scope": scope,
                    "provided_scopes": sorted(principal.scopes),
                },
            },
        )

    return dependency