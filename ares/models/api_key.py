from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        Index("ix_api_keys_is_active_expires_at", "is_active", "expires_at"),
        Index("ix_api_keys_rotated_from_key_id", "rotated_from_key_id"),
        Index("ix_api_keys_rotated_to_key_id", "rotated_to_key_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rate_limit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    api_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rotated_from_key_id: Mapped[str | None] = mapped_column(String, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    rotated_to_key_id: Mapped[str | None] = mapped_column(String, ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True)
    rotation_grace_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
