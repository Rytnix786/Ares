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