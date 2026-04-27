from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class ModelChampion(Base):
    __tablename__ = "model_champions"
    __table_args__ = (
        Index("uq_active_champion_per_model", "model_name", unique=True, postgresql_where=text("is_active = true")),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    champion_run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.id"), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    promoted_by: Mapped[str] = mapped_column(String(256), nullable=False)
    promotion_reason: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)