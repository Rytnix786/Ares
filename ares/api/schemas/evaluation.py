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