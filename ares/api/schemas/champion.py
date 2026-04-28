from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PromoteChampionRequest(BaseModel):
    run_id: str
    promoted_by: str = "api"
    reason: str | None = None


class ChampionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    model_name: str
    champion_run_id: str
    promoted_at: str
    promoted_by: str
    promotion_reason: str | None = None
    is_active: bool


class ChampionEvaluationSnapshot(BaseModel):
    id: str | None = None
    commit_sha: str
    model_version: str
    golden_set_version: str
    metrics: dict[str, float] = Field(default_factory=dict)
    passed: bool | None = None
    failure_reason: str | None = None
    created_at: str | None = None
    artifact_uri: str | None = None


class ChampionExportEntry(BaseModel):
    model_name: str
    champion_run_id: str
    promoted_at: str
    promoted_by: str
    evaluation: ChampionEvaluationSnapshot | None = None


class ChampionExportResponse(BaseModel):
    version: int
    champions: list[ChampionExportEntry] = Field(default_factory=list)


class ChampionHistoryEntry(BaseModel):
    id: str
    model_name: str
    champion_run_id: str
    promoted_at: str
    promoted_by: str
    promotion_reason: str | None = None
    is_active: bool
    evaluation: ChampionEvaluationSnapshot | None = None


class ChampionHistoryResponse(BaseModel):
    model_name: str
    history: list[ChampionHistoryEntry] = Field(default_factory=list)