"""Drift scheduler service for automated monitoring."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ares.db import crud
from ares.drift.runner import run_drift_job
from ares.models import DriftJob, DriftJobRun

logger = logging.getLogger(__name__)


class DriftScheduler:
    """Executes due drift jobs through the shared DriftJobRunner function.

    Duplicate prevention is implemented as an atomic-enough claim for this service:
    a running run newer than the last scheduler window causes the job to be skipped.
    The actual drift execution remains in ``ares.drift.runner.run_drift_job`` so CLI,
    API, scheduler, worker, and future Kubernetes CronJobs share one code path.
    """

    def __init__(self, session_factory: Any | None = None) -> None:
        self.session_factory = session_factory
        self.logger = logger

    async def execute_due_jobs(self, db_session: AsyncSession) -> dict[str, Any]:
        result: dict[str, Any] = {"executed": 0, "skipped": 0, "failed": 0, "jobs": []}
        for job in await crud.list_due_drift_jobs(db_session):
            job_result = await self._execute_single_job(db_session, job)
            result["jobs"].append(job_result)
            result[job_result["status"]] = int(result.get(job_result["status"], 0)) + 1
        return result

    async def _execute_single_job(self, db_session: AsyncSession, job: DriftJob) -> dict[str, Any]:
        running = await self._get_running_run(db_session, job.id)
        if running is not None:
            return {"status": "skipped", "job_id": job.id, "run_id": running.id, "reason": "duplicate_in_progress"}
        summary = await run_drift_job(db_session, job)
        status = "executed" if summary.status == "success" else "failed"
        return {"status": status, "job_id": job.id, "run_id": summary.run_id, "model_name": job.model_name}

    async def _get_running_run(self, db_session: AsyncSession, job_id: str) -> DriftJobRun | None:
        runs = await crud.list_drift_job_runs(db_session, job_id=job_id, limit=5)
        return next((run for run in runs if run.status == "running"), None)

    async def schedule_job(self, db_session: AsyncSession, job: DriftJob, start_immediately: bool = False) -> bool:
        job.status = "active"
        if start_immediately or job.next_run_at is None:
            job.next_run_at = datetime.utcnow()
        await db_session.flush()
        return True

    async def unschedule_job(self, db_session: AsyncSession, job_id: str) -> bool:
        job = await crud.get_drift_job(db_session, job_id)
        if job is None:
            return False
        job.status = "inactive"
        await db_session.flush()
        return True
