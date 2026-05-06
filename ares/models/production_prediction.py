from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ares.models.base import Base


class ProductionPredictionBatchRecord(Base):
    """Persisted production prediction batch for drift monitoring."""

    __tablename__ = "production_prediction_batches"
    __table_args__ = (
        Index("ix_prediction_batches_model_created_at", "model_name", "created_at"),
        Index("ix_prediction_batches_source_created_at", "source", "created_at"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="api_push")
    rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    received_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
