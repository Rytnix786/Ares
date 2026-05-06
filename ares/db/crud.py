from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.cache.keys import cache_key
from ares.exceptions import (
    AresException,
    PromotionError,
)
from ares.models import (
    AlertEvent,
    AuditLog,
    ChampionRollback,
    DriftJob,
    DriftJobRun,
    DriftReportRecord,
    EvaluationRun,
    ModelChampion,
    ProductionPredictionBatchRecord,
    SliceMetricPoint,
)
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
    await persist_slice_metric_points(db, run)
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
            await db.flush()
            rollback_record = ChampionRollback(
                model_name=model_name,
                from_champion_id=current.id,
                to_champion_id=champion.id,
                from_run_id=current.champion_run_id,
                to_run_id=target_run_id,
                actor=rolled_back_by,
                reason=reason,
                validation_status="validated",
                status="completed",
                completed_at=datetime.utcnow(),
                rollback_metadata={"target_run_id": target_run_id},
            )
            db.add(rollback_record)
        if not dry_run:
            await db.refresh(champion)
            await db.refresh(rollback_record)
        return {"model_name": model_name, "from_champion": current, "to_run_id": target_run_id, "champion": champion, "rollback": rollback_record, "dry_run": False}
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


async def list_champion_rollbacks(db: AsyncSession, model_name: str, limit: int = 100) -> list[ChampionRollback]:
    result = await db.execute(
        select(ChampionRollback)
        .where(ChampionRollback.model_name == model_name)
        .order_by(ChampionRollback.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_prediction_batch(db: AsyncSession, **values: Any) -> ProductionPredictionBatchRecord:
    batch = ProductionPredictionBatchRecord(**values)
    db.add(batch)
    await db.flush()
    await db.refresh(batch)
    return batch


async def latest_prediction_batch(db: AsyncSession, model_name: str, source: str | None = None) -> ProductionPredictionBatchRecord | None:
    stmt = select(ProductionPredictionBatchRecord).where(ProductionPredictionBatchRecord.model_name == model_name)
    if source:
        stmt = stmt.where(ProductionPredictionBatchRecord.source == source)
    result = await db.execute(stmt.order_by(ProductionPredictionBatchRecord.created_at.desc()).limit(1))
    return result.scalar_one_or_none()


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


async def create_drift_job(db: AsyncSession, **values: Any) -> DriftJob:
    job = DriftJob(**values)
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_drift_job(db: AsyncSession, job_id: str) -> DriftJob | None:
    return await db.get(DriftJob, job_id)


async def list_drift_jobs(db: AsyncSession, model_name: str | None = None, status: str | None = None, limit: int = 100) -> list[DriftJob]:
    stmt = select(DriftJob).order_by(DriftJob.created_at.desc()).limit(limit)
    if model_name:
        stmt = stmt.where(DriftJob.model_name == model_name)
    if status:
        stmt = stmt.where(DriftJob.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_drift_job_run(db: AsyncSession, **values: Any) -> DriftJobRun:
    run = DriftJobRun(**values)
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def persist_slice_metric_points(db: AsyncSession, run: EvaluationRun) -> list[SliceMetricPoint]:
    points: list[SliceMetricPoint] = []
    for slice_name, metrics in (run.slice_metrics or {}).items():
        is_critical = bool(metrics.get("is_critical", False))
        for metric_name, value in metrics.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            point = SliceMetricPoint(
                run_id=run.id,
                model_name=run.model_name,
                slice_name=str(slice_name),
                metric_name=str(metric_name),
                metric_value=float(value),
                is_critical=is_critical,
                created_at=run.created_at,
            )
            db.add(point)
            points.append(point)
    if points:
        await db.flush()
    return points


async def list_slice_metric_trends(
    db: AsyncSession,
    *,
    model_name: str | None = None,
    slice_name: str | None = None,
    metric_name: str | None = None,
    limit: int = 500,
) -> list[SliceMetricPoint]:
    stmt = select(SliceMetricPoint).order_by(SliceMetricPoint.created_at.desc()).limit(limit)
    if model_name:
        stmt = stmt.where(SliceMetricPoint.model_name == model_name)
    if slice_name:
        stmt = stmt.where(SliceMetricPoint.slice_name == slice_name)
    if metric_name:
        stmt = stmt.where(SliceMetricPoint.metric_name == metric_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def purge_slice_metric_points(db: AsyncSession, *, older_than: datetime) -> int:
    result = await db.execute(delete(SliceMetricPoint).where(SliceMetricPoint.created_at < older_than))
    await db.flush()
    return int(getattr(result, "rowcount", 0) or 0)


async def attach_model_card(db: AsyncSession, run_id: str, *, markdown_uri: str, payload: dict[str, Any]) -> EvaluationRun | None:
    run = await db.get(EvaluationRun, run_id)
    if run is None:
        return None
    run.model_card_uri = markdown_uri
    run.model_card_json = payload
    await db.flush()
    await db.refresh(run)
    return run


async def update_drift_job_run(db: AsyncSession, run_id: str, **values: Any) -> DriftJobRun | None:
    run = await db.get(DriftJobRun, run_id)
    if run is None:
        return None
    for key, value in values.items():
        setattr(run, key, value)
    await db.flush()
    await db.refresh(run)
    return run


async def list_drift_job_runs(db: AsyncSession, job_id: str | None = None, model_name: str | None = None, limit: int = 100) -> list[DriftJobRun]:
    stmt = select(DriftJobRun).order_by(DriftJobRun.created_at.desc()).limit(limit)
    if job_id:
        stmt = stmt.where(DriftJobRun.job_id == job_id)
    if model_name:
        stmt = stmt.where(DriftJobRun.model_name == model_name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_due_drift_jobs(db: AsyncSession, now: datetime | None = None, limit: int = 100) -> list[DriftJob]:
    now = now or datetime.utcnow()
    result = await db.execute(
        select(DriftJob)
        .where(DriftJob.status == "active", DriftJob.next_run_at <= now)
        .order_by(DriftJob.next_run_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def mark_drift_job_scheduled(db: AsyncSession, job: DriftJob, *, interval_minutes: int = 60) -> None:
    now = datetime.utcnow()
    job.last_run_at = now
    job.next_run_at = now + timedelta(minutes=interval_minutes)
    job.updated_at = now
    await db.flush()


async def create_alert_event(db: AsyncSession, **values: Any) -> AlertEvent:
    dedupe_key = values.get("dedupe_key")
    if dedupe_key:
        existing = await db.execute(
            select(AlertEvent).where(AlertEvent.dedupe_key == dedupe_key, AlertEvent.status.in_(["open", "acknowledged"]))
        )
        event = existing.scalar_one_or_none()
        if event is not None:
            event.payload = {**(event.payload or {}), **dict(values.get("payload") or {})}
            event.message = values.get("message") or event.message
            await db.flush()
            await db.refresh(event)
            return event
    event = AlertEvent(**values)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def list_alert_events(db: AsyncSession, model_name: str | None = None, status: str | None = None, limit: int = 100) -> list[AlertEvent]:
    stmt = select(AlertEvent).order_by(AlertEvent.created_at.desc()).limit(limit)
    if model_name:
        stmt = stmt.where(AlertEvent.model_name == model_name)
    if status:
        stmt = stmt.where(AlertEvent.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_alert_event_status(db: AsyncSession, event_id: str, status: str, actor: str | None = None) -> AlertEvent | None:
    event = await db.get(AlertEvent, event_id)
    if event is None:
        return None
    now = datetime.utcnow()
    event.status = status
    if status == "acknowledged":
        event.acknowledged_at = now
        event.acknowledged_by = actor
    if status == "resolved":
        event.resolved_at = now
        event.resolved_by = actor
    await db.flush()
    await db.refresh(event)
    return event


async def list_audit_logs(
    db: AsyncSession,
    *,
    user: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    if user:
        stmt = stmt.where(AuditLog.user == user)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def purge_audit_logs(db: AsyncSession, *, older_than: datetime) -> int:
    result = await db.execute(delete(AuditLog).where(AuditLog.timestamp < older_than))
    await db.flush()
    return int(getattr(result, "rowcount", 0) or 0)
