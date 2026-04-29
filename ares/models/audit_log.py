"""Audit log model for tracking mutations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class AuditLog(Base):
    """Audit log for tracking all mutations."""
    
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    user: Mapped[str] = mapped_column(String(256), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False)  # success, error
    status_code: Mapped[int] = mapped_column(String(16), nullable=True)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
