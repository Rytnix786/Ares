from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class DriftReportRecord(Base):
    __tablename__ = "drift_reports"
    __table_args__ = (
        Index("ix_drift_reports_model_name_created_at", "model_name", "created_at"),
        Index("ix_drift_reports_is_alerting_created_at", "is_alerting", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    feature: Mapped[str] = mapped_column(String(256), nullable=False)
    kl_divergence: Mapped[float] = mapped_column(Float, nullable=False)
    psi: Mapped[float] = mapped_column(Float, nullable=False)
    is_alerting: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    job_id: Mapped[str | None] = mapped_column(String, ForeignKey("drift_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String, ForeignKey("drift_job_runs.id", ondelete="SET NULL"), nullable=True, index=True)
