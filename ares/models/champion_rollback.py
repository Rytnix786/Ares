from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class ChampionRollback(Base):
    """First-class governed rollback record."""

    __tablename__ = "champion_rollbacks"
    __table_args__ = (Index("ix_champion_rollbacks_model_created_at", "model_name", "created_at"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    from_champion_id: Mapped[str] = mapped_column(String, ForeignKey("model_champions.id", ondelete="SET NULL"), nullable=True, index=True)
    to_champion_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_champions.id", ondelete="SET NULL"), nullable=True, index=True)
    from_run_id: Mapped[str] = mapped_column(String, nullable=False)
    to_run_id: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String(256), nullable=False)
    reason: Mapped[str] = mapped_column(String(1024), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(64), nullable=False, default="validated")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rollback_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
