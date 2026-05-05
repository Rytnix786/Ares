"""Drift scheduler service for automated monitoring."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ares.db.crud import create_drift_job_run, get_drift_job, list_drift_jobs
from ares.drift.runner import DriftJobRunner
from ares.models import DriftJob, DriftJobRun

logger = logging.getLogger(__name__)


class DriftScheduler:
    """Manages scheduled drift job execution with duplicate prevention."""

    def __init__(self, session_factory, drift_runner: Optional[DriftJobRunner] = None):
        """Initialize scheduler with database session factory and drift runner.
        
        Args:
            session_factory: AsyncSessionMaker for database access
            drift_runner: DriftJobRunner instance, defaults to new instance
        """
        self.session_factory = session_factory
        self.drift_runner = drift_runner or DriftJobRunner()
        self.logger = logger

    async def execute_due_jobs(self, db_session: AsyncSession) -> dict:
        """Execute all jobs whose next_run_at <= now.
        
        Returns:
            dict with 'executed', 'skipped', 'failed' job counts and details
        """
        result = {"executed": 0, "skipped": 0, "failed": 0, "jobs": []}
        now = datetime.utcnow()

        try:
            jobs = await list_drift_jobs(db_session, status="active")
            
            for job in jobs:
                if job.next_run_at and job.next_run_at <= now:
                    job_result = await self._execute_single_job(db_session, job, now)
                    
                    if job_result["status"] == "executed":
                        result["executed"] += 1
                    elif job_result["status"] == "skipped":
                        result["skipped"] += 1
                    else:
                        result["failed"] += 1
                    
                    result["jobs"].append(job_result)
            
            return result
        except Exception as e:
            self.logger.error(f"Error executing due jobs: {e}", exc_info=True)
            result["error"] = str(e)
            return result

    async def _execute_single_job(
        self, db_session: AsyncSession, job: DriftJob, now: datetime
    ) -> dict:
        """Execute a single drift job with duplicate prevention.
        
        Returns:
            dict with 'status' (executed/skipped/failed), job_id, run_id, error if any
        """
        job_result = {
            "job_id": job.id,
            "job_name": job.job_name,
            "model_name": job.model_name,
            "status": "pending",
        }

        try:
            # Check for duplicate in-flight run (duplicate prevention)
            recent_run = await self._get_recent_run(db_session, job.id)
            if recent_run and recent_run.status == "running":
                self.logger.info(
                    f"Skipping job {job.id}: duplicate run {recent_run.id} already in progress"
                )
                job_result["status"] = "skipped"
                job_result["reason"] = "duplicate_in_progress"
                return job_result

            # Create job run record
            run = await create_drift_job_run(
                db_session,
                job_id=job.id,
                started_at=now,
                status="running",
            )
            job_result["run_id"] = run.id

            # Execute drift check via runner
            runner_result = await self.drift_runner.run_drift_check(
                db_session, job, run
            )

            # Update run status based on result
            if runner_result.get("success"):
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                job_result["status"] = "executed"
                self.logger.info(f"Job {job.id} run {run.id} completed successfully")
            else:
                run.status = "failed"
                run.error_message = runner_result.get("error", "Unknown error")
                run.completed_at = datetime.utcnow()
                job_result["status"] = "failed"
                job_result["error"] = run.error_message
                self.logger.error(
                    f"Job {job.id} run {run.id} failed: {run.error_message}"
                )

            # Update next run time (add job's interval)
            if hasattr(job, "interval_minutes") and job.interval_minutes:
                job.next_run_at = now + timedelta(minutes=job.interval_minutes)
            else:
                job.next_run_at = now + timedelta(hours=1)  # Default 1 hour

            await db_session.flush()

        except Exception as e:
            self.logger.error(f"Error executing job {job.id}: {e}", exc_info=True)
            job_result["status"] = "failed"
            job_result["error"] = str(e)

        return job_result

    async def _get_recent_run(
        self, db_session: AsyncSession, job_id: str, minutes: int = 10
    ) -> Optional[DriftJobRun]:
        """Get most recent run for job within last N minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        stmt = (
            select(DriftJobRun)
            .where(DriftJobRun.job_id == job_id)
            .where(DriftJobRun.started_at >= cutoff)
            .order_by(DriftJobRun.started_at.desc())
            .limit(1)
        )
        result = await db_session.execute(stmt)
        return result.scalar_one_or_none()

    async def schedule_job(
        self, db_session: AsyncSession, job: DriftJob, start_immediately: bool = False
    ) -> bool:
        """Schedule a job to run.
        
        Args:
            db_session: Database session
            job: DriftJob to schedule
            start_immediately: If True, set next_run_at to now
            
        Returns:
            True if successfully scheduled
        """
        try:
            if start_immediately:
                job.next_run_at = datetime.utcnow()
            else:
                job.next_run_at = job.next_run_at or datetime.utcnow()
            
            job.status = "active"
            await db_session.flush()
            self.logger.info(f"Scheduled job {job.id} with next_run_at: {job.next_run_at}")
            return True
        except Exception as e:
            self.logger.error(f"Error scheduling job {job.id}: {e}")
            return False

    async def unschedule_job(self, db_session: AsyncSession, job_id: str) -> bool:
        """Unschedule a job.
        
        Args:
            db_session: Database session
            job_id: Job ID to unschedule
            
        Returns:
            True if successfully unscheduled
        """
        try:
            job = await get_drift_job(db_session, job_id)
            if not job:
                self.logger.warning(f"Job {job_id} not found")
                return False
            
            job.status = "inactive"
            await db_session.flush()
            self.logger.info(f"Unscheduled job {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error unscheduling job {job_id}: {e}")
            return False
