from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_api_key
from ares.api.limiting import limiter
from ares.api.schemas.champion import (
    ChampionEvaluationSnapshot,
    ChampionExportEntry,
    ChampionExportResponse,
    ChampionResponse,
    PromoteChampionRequest,
)
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db

router = APIRouter(prefix="/api/v1/champions", tags=["champions"], dependencies=[Depends(require_api_key)])


@router.get("/export", response_model=ChampionExportResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def export(request: Request, db: AsyncSession = Depends(get_db)) -> ChampionExportResponse:
    payload = await crud.export_champions(db)
    champions = []
    for item in payload.get("champions", []):
        evaluation = item.get("evaluation")
        champions.append(
            ChampionExportEntry(
                model_name=item["model_name"],
                champion_run_id=item["champion_run_id"],
                promoted_at=item["promoted_at"],
                promoted_by=item["promoted_by"],
                evaluation=ChampionEvaluationSnapshot(**evaluation) if evaluation else None,
            )
        )
    return ChampionExportResponse(version=int(payload.get("version", 1)), champions=champions)


@router.get("/{model_name}", response_model=ChampionResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_champion(request: Request, model_name: str, db: AsyncSession = Depends(get_db)) -> ChampionResponse:
    champion = await crud.get_active_champion(db, model_name)
    if champion is None:
        raise HTTPException(status_code=404, detail="Champion not found")
    return ChampionResponse(
        id=champion.id,
        model_name=champion.model_name,
        champion_run_id=champion.champion_run_id,
        promoted_at=champion.promoted_at.isoformat(),
        promoted_by=champion.promoted_by,
        promotion_reason=champion.promotion_reason,
        is_active=champion.is_active,
    )


@router.post("/{model_name}/promote", response_model=ChampionResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def promote(request: Request, model_name: str, payload: PromoteChampionRequest, db: AsyncSession = Depends(get_db)) -> ChampionResponse:
    champion = await crud.promote_champion(db, model_name, payload.run_id, payload.promoted_by, payload.reason)
    return ChampionResponse(
        id=champion.id,
        model_name=champion.model_name,
        champion_run_id=champion.champion_run_id,
        promoted_at=champion.promoted_at.isoformat(),
        promoted_by=champion.promoted_by,
        promotion_reason=champion.promotion_reason,
        is_active=champion.is_active,
    )


@router.get("/{model_name}/previous", response_model=ChampionResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def previous(request: Request, model_name: str, db: AsyncSession = Depends(get_db)) -> ChampionResponse:
    champion = await crud.get_previous_champion(db, model_name)
    if champion is None:
        raise HTTPException(status_code=404, detail="Previous champion not found")
    return ChampionResponse(
        id=champion.id,
        model_name=champion.model_name,
        champion_run_id=champion.champion_run_id,
        promoted_at=champion.promoted_at.isoformat(),
        promoted_by=champion.promoted_by,
        promotion_reason=champion.promotion_reason,
        is_active=champion.is_active,
    )