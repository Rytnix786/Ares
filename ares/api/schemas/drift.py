from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DriftReportIn(BaseModel):
    model_name: str
    feature: str
    kl_divergence: float
    psi: float
    is_alerting: bool
    severity: str
    payload: dict[str, Any] = Field(default_factory=dict)
    job_id: str | None = None
    run_id: str | None = None


class DriftReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    feature: str
    kl_divergence: float
    psi: float
    is_alerting: bool
    severity: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
    job_id: str | None = None
    run_id: str | None = None


class DriftPredictionIngestRequest(BaseModel):
    model_name: str
    records: list[dict[str, Any]] = Field(min_length=1)
    source: str = "api_push"


class DriftPredictionIngestResponse(BaseModel):
    model_name: str
    rows: int
    columns: list[str]
    source: str


class DriftJobCreateRequest(BaseModel):
    model_name: str
    job_name: str
    schedule: str | None = None
    source_type: str = "local_file"
    source_config: dict[str, Any] = Field(default_factory=dict)
    reference_config: dict[str, Any] = Field(default_factory=dict)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"
    created_by: str | None = None


class DriftJobResponse(BaseModel):
    id: str
    model_name: str
    job_name: str
    schedule: str | None = None
    source_type: str
    source_config: dict[str, Any] = Field(default_factory=dict)
    reference_config: dict[str, Any] = Field(default_factory=dict)
    thresholds: dict[str, Any] = Field(default_factory=dict)
    status: str
    created_by: str | None = None
    created_at: str
    updated_at: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None


class DriftJobRunResponse(BaseModel):
    id: str
    job_id: str | None = None
    model_name: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    features_evaluated: int
    alerts_triggered: int
    max_severity: str | None = None
    error_message: str | None = None
    run_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str
