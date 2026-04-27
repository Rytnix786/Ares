from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        UniqueConstraint("commit_sha", "golden_set_version", "model_name", name="uq_evaluation_idempotency"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False, default="candidate")
    branch: Mapped[str] = mapped_column(String(256), nullable=False, default="unknown")
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_f1: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_accuracy: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_precision: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_recall: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_p50_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    latency_p99_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_size_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    slice_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    gate_config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    golden_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    n_samples_evaluated: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    mlflow_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    mlflow_error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)