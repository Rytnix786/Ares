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
    commit_sha: str
    model_version: str
    golden_set_version: str
    metrics: dict[str, float] = Field(default_factory=dict)


class ChampionExportEntry(BaseModel):
    model_name: str
    champion_run_id: str
    promoted_at: str
    promoted_by: str
    evaluation: ChampionEvaluationSnapshot | None = None


class ChampionExportResponse(BaseModel):
    version: int
    champions: list[ChampionExportEntry] = Field(default_factory=list)