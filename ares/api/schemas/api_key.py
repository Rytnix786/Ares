from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str
    key: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    rate_limit: str | None = None
    ttl_days: int | None = Field(default=None, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApiKeyRotateRequest(BaseModel):
    key: str | None = None
    name: str | None = None
    scopes: list[str] | None = None
    rate_limit: str | None = None
    ttl_days: int | None = Field(default=None, ge=1)
    grace_days: int = Field(default=0, ge=0)


class ApiKeyRevokeRequest(BaseModel):
    revoked_by: str | None = None
    reason: str | None = None


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    scopes: list[str]
    rate_limit: str | None = None
    is_active: bool
    created_at: datetime
    revoked_at: datetime | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    use_count: int
    revoked_by: str | None = None
    revocation_reason: str | None = None
    rotated_from_key_id: str | None = None
    rotated_to_key_id: str | None = None
    rotation_grace_expires_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    key: str
    record: ApiKeyResponse
