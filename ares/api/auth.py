from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request, status

from ares.config import settings


def rate_limit_key(request: Request) -> str:
    return request.headers.get("x-api-key") or (request.client.host if request.client else "anonymous")


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not settings.ARES_API_KEYS:
        if settings.ENVIRONMENT == "development":
            return "development"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="API keys are not configured")
    if x_api_key and any(hmac.compare_digest(x_api_key, allowed) for allowed in settings.ARES_API_KEYS):
        return x_api_key
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")