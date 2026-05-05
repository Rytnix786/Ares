from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class DriftJob(Base):
    __tablename__ = "drift_jobs"
    __table_args__ = (
        UniqueConstraint("model_name", "job_name", name="uq_drift_jobs_model_name_job_name"),
        Index("ix_drift_jobs_status_next_run_at", "status", "next_run_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(256), nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="local_file")
    source_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reference_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class DriftJobRun(Base):
    __tablename__ = "drift_job_runs"
    __table_args__ = (
        Index("ix_drift_job_runs_model_name_created_at", "model_name", "created_at"),
        Index("ix_drift_job_runs_status_created_at", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str | None] = mapped_column(String, ForeignKey("drift_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    features_evaluated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_triggered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
