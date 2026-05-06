from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    model_name: str
    commit_sha: str
    new_metrics: dict[str, float]
    slice_metrics: dict[str, Any] = Field(default_factory=dict)
    n_samples: int = 1


class MetricComparisonRow(BaseModel):
    champion: float
    candidate: float
    delta: float
    status: str


class SliceComparisonRow(BaseModel):
    slice: str
    champion_f1: float | None = None
    candidate_f1: float | None = None
    delta: float | None = None
    status: str
    threshold: float | None = None
    is_critical: bool = False


class ComparisonResponse(BaseModel):
    decision: str
    reason: str
    decision_narrative: str = ""
    delta_metrics: dict[str, float] = Field(default_factory=dict)
    champion_metrics: dict[str, float] = Field(default_factory=dict)
    new_metrics: dict[str, float] = Field(default_factory=dict)
    metric_table: dict[str, MetricComparisonRow] = Field(default_factory=dict)
    slice_regressions: list[dict[str, Any]] = Field(default_factory=list)
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    is_first_run: bool = False
    should_promote: bool = False


class SimulationRequest(BaseModel):
    run_id: str
    override_thresholds: dict[str, float] = Field(default_factory=dict)


class SimulationResponse(ComparisonResponse):
    run_id: str


class EvaluationRunResponse(BaseModel):
    id: str
    commit_sha: str
    model_name: str
    model_version: str
    passed: bool
    overall_f1: float
    overall_accuracy: float
    overall_precision: float | None = None
    overall_recall: float | None = None
    latency_p50_ms: float | None = None
    latency_p99_ms: float | None = None
    duration_seconds: float | None = None
    failure_reason: str | None = None
    golden_set_version: str | None = None
    mlflow_run_id: str | None = None
    artifact_uri: str | None = None
    model_card_uri: str | None = None
    slice_metrics: dict[str, Any] = Field(default_factory=dict)
    gate_config_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    champion_run_id: str | None = None
    is_current_champion: bool = False
    decision_narrative: str = ""
    champion_metrics: dict[str, float] = Field(default_factory=dict)
    delta_metrics: dict[str, float] = Field(default_factory=dict)
    metric_table: dict[str, MetricComparisonRow] = Field(default_factory=dict)
    slice_comparison: list[SliceComparisonRow] = Field(default_factory=list)
    created_at: str


class EvaluatorPluginResponse(BaseModel):
    name: str
    version: str
    description: str = ""


class SliceTrendPointResponse(BaseModel):
    run_id: str
    model_name: str
    slice_name: str
    metric_name: str
    metric_value: float
    is_critical: bool
    created_at: str


class SliceTrendRetentionResponse(BaseModel):
    deleted: int
    retention_days: int


class MultiModelCompareRequest(BaseModel):
    run_ids: list[str] = Field(min_length=2)


class MultiModelCompareRow(BaseModel):
    run_id: str
    model_name: str
    model_version: str
    passed: bool
    metrics: dict[str, float]
    risk_summary: str


class MultiModelCompareResponse(BaseModel):
    candidates: list[MultiModelCompareRow]
    winner_run_id: str | None = None
    winner_reason: str = ""
    winner: dict[str, Any] | None = None
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    rankings: list[dict[str, Any]] = Field(default_factory=list)


class ModelCardResponse(BaseModel):
    run_id: str
    markdown: str
    payload: dict[str, Any]
