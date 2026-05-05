from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class ModelChampion(Base):
    __tablename__ = "model_champions"
    __table_args__ = (
        Index("uq_active_champion_per_model", "model_name", unique=True, postgresql_where=text("is_active = true")),
        Index("ix_model_champions_action", "action"),
        Index("ix_model_champions_previous_champion_id", "previous_champion_id"),
        Index("ix_model_champions_rolled_back_from_id", "rolled_back_from_id"),
        Index("ix_model_champions_model_name_promoted_at", "model_name", "promoted_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    champion_run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.id"), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    promoted_by: Mapped[str] = mapped_column(String(256), nullable=False)
    promotion_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    previous_champion_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_champions.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="promotion")
    rolled_back_from_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_champions.id", ondelete="SET NULL"), nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rollback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lifecycle_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True, default=dict)
