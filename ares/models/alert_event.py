from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        Index("ix_alert_events_status_created_at", "status", "created_at"),
        Index("ix_alert_events_model_name_created_at", "model_name", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    drift_report_id: Mapped[str | None] = mapped_column(String, ForeignKey("drift_reports.id", ondelete="SET NULL"), nullable=True, index=True)
    drift_run_id: Mapped[str | None] = mapped_column(String, ForeignKey("drift_job_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    evaluation_run_id: Mapped[str | None] = mapped_column(String, ForeignKey("evaluation_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
