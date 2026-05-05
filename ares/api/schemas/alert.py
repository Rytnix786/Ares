from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AlertEventResponse(BaseModel):
    id: str
    event_type: str
    source: str
    model_name: str | None = None
    severity: str
    status: str
    dedupe_key: str | None = None
    drift_report_id: str | None = None
    drift_run_id: str | None = None
    evaluation_run_id: str | None = None
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None


class AlertStatusUpdateRequest(BaseModel):
    status: str = Field(pattern="^(open|acknowledged|resolved)$")
    actor: str | None = None
