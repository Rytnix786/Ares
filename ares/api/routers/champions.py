from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ares.api.auth import require_scope
from ares.api.limiting import limiter
from ares.api.presenters import extract_metrics
from ares.api.schemas.champion import (
    ChampionEvaluationSnapshot,
    ChampionExportEntry,
    ChampionExportResponse,
    ChampionHistoryEntry,
    ChampionHistoryResponse,
    ChampionResponse,
    ChampionRollbackRecordResponse,
    ChampionRollbackRequest,
    ChampionRollbackResponse,
    PromoteChampionRequest,
)
from ares.config import settings
from ares.db import crud
from ares.db.session import get_db
from ares.model_cards import generate_model_card

router = APIRouter(prefix="/api/v1/champions", tags=["champions"])


def _snapshot_from_run(run: Any) -> ChampionEvaluationSnapshot | None:
    if run is None:
        return None
    return ChampionEvaluationSnapshot(
        id=run.id,
        commit_sha=run.commit_sha,
        model_version=run.model_version,
        golden_set_version=run.golden_set_version,
        metrics=extract_metrics(run),
        passed=run.passed,
        failure_reason=run.failure_reason,
        created_at=run.created_at.isoformat(),
        artifact_uri=run.artifact_uri,
    )


@router.get("/export", response_model=ChampionExportResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def export(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> ChampionExportResponse:
    del request
    payload = await crud.export_champions(db)
    champions = []
    for item in payload.get("champions", []):
        run = await crud.get_evaluation_run(db, item["champion_run_id"])
        champions.append(
            ChampionExportEntry(
                model_name=item["model_name"],
                champion_run_id=item["champion_run_id"],
                promoted_at=item["promoted_at"],
                promoted_by=item["promoted_by"],
                evaluation=_snapshot_from_run(run),
            )
        )
    return ChampionExportResponse(version=int(payload.get("version", 1)), champions=champions)


@router.get("/{model_name}", response_model=ChampionResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def get_champion(
    request: Request,
    model_name: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> ChampionResponse:
    del request
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
async def promote(
    request: Request,
    model_name: str,
    payload: PromoteChampionRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("write")),
) -> ChampionResponse:
    del request
    champion = await crud.promote_champion(db, model_name, payload.run_id, payload.promoted_by, payload.reason)
    run = await crud.get_evaluation_run(db, payload.run_id)
    if run is not None and run.model_card_uri is None:
        card = generate_model_card(
            run,
            champion=champion,
            drift_reports=await crud.list_drift_reports(db, model_name=model_name, limit=20),
            champion_history=await crud.list_champion_history(db, model_name),
        )
        await crud.attach_model_card(db, run.id, markdown_uri=f"ares://model-cards/{run.id}.md", payload=card.payload)
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
async def previous(
    request: Request,
    model_name: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> ChampionResponse:
    del request
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


@router.get("/{model_name}/history", response_model=ChampionHistoryResponse)
@limiter.limit(settings.RATE_LIMIT_READ)
async def history(
    request: Request,
    model_name: str,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> ChampionHistoryResponse:
    del request
    history_rows = await crud.list_champion_history(db, model_name)
    return ChampionHistoryResponse(
        model_name=model_name,
        history=[
            ChampionHistoryEntry(
                id=entry.id,
                model_name=entry.model_name,
                champion_run_id=entry.champion_run_id,
                promoted_at=entry.promoted_at.isoformat(),
                promoted_by=entry.promoted_by,
                promotion_reason=entry.promotion_reason,
                is_active=entry.is_active,
                evaluation=_snapshot_from_run(await crud.get_evaluation_run(db, entry.champion_run_id)),
            )
            for entry in history_rows
        ],
    )


def _rollback_record_response(row: Any) -> ChampionRollbackRecordResponse:
    return ChampionRollbackRecordResponse(
        id=row.id,
        model_name=row.model_name,
        from_champion_id=row.from_champion_id,
        to_champion_id=row.to_champion_id,
        from_run_id=row.from_run_id,
        to_run_id=row.to_run_id,
        actor=row.actor,
        reason=row.reason,
        validation_status=row.validation_status,
        status=row.status,
        created_at=row.created_at.isoformat(),
        completed_at=None if row.completed_at is None else row.completed_at.isoformat(),
        rollback_metadata=row.rollback_metadata,
    )


@router.post("/{model_name}/rollback", response_model=ChampionRollbackResponse)
@limiter.limit(settings.RATE_LIMIT_CHAMPION_MUTATION)
async def rollback(
    request: Request,
    model_name: str,
    payload: ChampionRollbackRequest,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("admin")),
) -> ChampionRollbackResponse:
    del request, _principal
    result = await crud.rollback_champion(
        db,
        model_name,
        rolled_back_by=payload.rolled_back_by,
        reason=payload.reason,
        target_run_id=payload.target_run_id,
        dry_run=payload.dry_run,
    )
    champion = result["champion"]
    return ChampionRollbackResponse(
        model_name=model_name,
        from_champion_id=result["from_champion"].id,
        from_run_id=result["from_champion"].champion_run_id,
        to_run_id=result["to_run_id"],
        rolled_back_by=payload.rolled_back_by,
        reason=payload.reason,
        dry_run=payload.dry_run,
        champion=None
        if champion is None
        else ChampionResponse(
            id=champion.id,
            model_name=champion.model_name,
            champion_run_id=champion.champion_run_id,
            promoted_at=champion.promoted_at.isoformat(),
            promoted_by=champion.promoted_by,
            promotion_reason=champion.promotion_reason,
            is_active=champion.is_active,
        ),
    )


@router.get("/{model_name}/rollbacks", response_model=list[ChampionRollbackRecordResponse])
@limiter.limit(settings.RATE_LIMIT_READ)
async def rollbacks(
    request: Request,
    model_name: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _principal: object = Depends(require_scope("read")),
) -> list[ChampionRollbackRecordResponse]:
    del request, _principal
    return [_rollback_record_response(row) for row in await crud.list_champion_rollbacks(db, model_name, limit=limit)]
