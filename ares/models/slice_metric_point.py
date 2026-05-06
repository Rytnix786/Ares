from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class SliceMetricPoint(Base):
    __tablename__ = "slice_metric_points"
    __table_args__ = (
        Index("ix_slice_metric_points_model_slice_metric", "model_name", "slice_name", "metric_name", "created_at"),
        Index("ix_slice_metric_points_critical_created_at", "is_critical", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String, ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    slice_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
