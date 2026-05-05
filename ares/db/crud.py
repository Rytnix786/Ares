from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.cache.keys import cache_key
from ares.exceptions import (
    AresException,
    PromotionError,
)
from ares.models import DriftReportRecord, EvaluationRun, ModelChampion
from ares.observability.metrics import cache_operations_total, evaluation_runs_total


async def get_evaluation_run(db: AsyncSession, run_id: str) -> EvaluationRun | None:
    cache_operations_total.labels("get_evaluation_run", "miss").inc()
    return await db.get(EvaluationRun, run_id)


async def get_cached_evaluation(db: AsyncSession, commit_sha: str, golden_set_version: str, model_name: str) -> EvaluationRun | None:
    cache_key("evaluation", commit_sha, golden_set_version, model_name)
    cache_operations_total.labels("get_cached_evaluation", "miss").inc()
    result = await db.execute(select(EvaluationRun).where(EvaluationRun.commit_sha == commit_sha, EvaluationRun.golden_set_version == golden_set_version, EvaluationRun.model_name == model_name))
    return result.scalar_one_or_none()


async def list_evaluation_runs(db: AsyncSession, limit: int = 100) -> list[EvaluationRun]:
    result = await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(limit))
    return list(result.scalars().all())


async def create_evaluation_run(db: AsyncSession, **values: Any) -> EvaluationRun:
    run = EvaluationRun(**values)
    db.add(run)
    await db.flush()
    await db.refresh(run)
    evaluation_runs_total.labels("passed" if run.passed else "failed").inc()
    return run


async def get_active_champion(db: AsyncSession, model_name: str) -> ModelChampion | None:
    result = await db.execute(select(ModelChampion).where(ModelChampion.model_name == model_name, ModelChampion.is_active.is_(True)))
    return result.scalar_one_or_none()


async def get_previous_champion(db: AsyncSession, model_name: str) -> ModelChampion | None:
    result = await db.execute(select(ModelChampion).where(ModelChampion.model_name == model_name, ModelChampion.is_active.is_(False)).order_by(ModelChampion.promoted_at.desc()).limit(1))
    return result.scalar_one_or_none()


async def list_champion_history(db: AsyncSession, model_name: str) -> list[ModelChampion]:
    result = await db.execute(
        select(ModelChampion)
        .where(ModelChampion.model_name == model_name)
        .order_by(ModelChampion.promoted_at.desc())
    )
    return list(result.scalars().all())


async def promote_champion(db: AsyncSession, model_name: str, run_id: str, promoted_by: str, reason: str | None = None) -> ModelChampion:
    try:
        async with (db.begin_nested() if db.in_transaction() else db.begin()):
            current_result = await db.execute(select(ModelChampion).where(ModelChampion.model_name == model_name, ModelChampion.is_active.is_(True)).with_for_update())
            current = current_result.scalar_one_or_none()
            if current:
                current.is_active = False
            champion = ModelChampion(model_name=model_name, champion_run_id=run_id, promoted_by=promoted_by, promotion_reason=reason, is_active=True, previous_champion_id=None if current is None else current.id, action="promotion")
            db.add(champion)
        await db.refresh(champion)
        return champion
    except AresException:
        raise
    except Exception as e:
        raise PromotionError(
            model_name=model_name,
            reason=str(e),
        ) from e


async def rollback_champion(
    db: AsyncSession,
    model_name: str,
    *,
    rolled_back_by: str,
    reason: str,
    target_run_id: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not reason.strip():
        raise PromotionError(model_name=model_name, reason="rollback reason is required")
    try:
        async with (db.begin_nested() if db.in_transaction() else db.begin()):
            current_result = await db.execute(select(ModelChampion).where(ModelChampion.model_name == model_name, ModelChampion.is_active.is_(True)).with_for_update())
            current = current_result.scalar_one_or_none()
            if current is None:
                raise PromotionError(model_name=model_name, reason="no active champion to roll back")
            if target_run_id is None:
                target = await get_previous_champion(db, model_name)
                if target is None:
                    raise PromotionError(model_name=model_name, reason="no previous champion available")
                target_run_id = target.champion_run_id
            target_run = await get_evaluation_run(db, target_run_id)
            if target_run is None:
                raise PromotionError(model_name=model_name, reason="target evaluation run not found", details={"target_run_id": target_run_id})
            if target_run.model_name != model_name:
                raise PromotionError(model_name=model_name, reason="target run belongs to a different model", details={"target_run_id": target_run_id, "target_model_name": target_run.model_name})
            if not target_run.passed:
                raise PromotionError(model_name=model_name, reason="target run did not pass the gate", details={"target_run_id": target_run_id})
            if dry_run:
                return {"model_name": model_name, "from_champion": current, "to_run_id": target_run_id, "champion": None, "dry_run": True}
            current.is_active = False
            champion = ModelChampion(
                model_name=model_name,
                champion_run_id=target_run_id,
                promoted_by=rolled_back_by,
                promotion_reason=reason,
                is_active=True,
                previous_champion_id=current.id,
                action="rollback",
                rolled_back_from_id=current.id,
                rollback_reason=reason,
                rollback_at=datetime.utcnow(),
                lifecycle_metadata={"target_run_id": target_run_id},
            )
            db.add(champion)
        if not dry_run:
            await db.refresh(champion)
        return {"model_name": model_name, "from_champion": current, "to_run_id": target_run_id, "champion": champion, "dry_run": False}
    except AresException:
        raise
    except Exception as e:
        raise PromotionError(model_name=model_name, reason=str(e)) from e


async def export_champions(db: AsyncSession) -> dict[str, Any]:
    result = await db.execute(select(ModelChampion).where(ModelChampion.is_active.is_(True)))
    champions = []
    for champion in result.scalars().all():
        run = await get_evaluation_run(db, champion.champion_run_id)
        champions.append({"model_name": champion.model_name, "champion_run_id": champion.champion_run_id, "promoted_at": champion.promoted_at.isoformat(), "promoted_by": champion.promoted_by, "evaluation": None if run is None else {"commit_sha": run.commit_sha, "model_version": run.model_version, "golden_set_version": run.golden_set_version, "metrics": {"overall_f1": run.overall_f1, "overall_accuracy": run.overall_accuracy}}})
    return {"version": 1, "champions": champions}


async def create_drift_report(db: AsyncSession, **values: Any) -> DriftReportRecord:
    report = DriftReportRecord(**values)
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def list_drift_reports(db: AsyncSession, model_name: str | None = None, limit: int = 100) -> list[DriftReportRecord]:
    stmt = select(DriftReportRecord).order_by(DriftReportRecord.created_at.desc()).limit(limit)
    if model_name:
        stmt = stmt.where(DriftReportRecord.model_name == model_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())
