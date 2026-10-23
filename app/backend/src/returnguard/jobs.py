"""The durable job queue (a `jobs` table; no Redis).

- Jobs are written in the same transaction as the work they describe (outbox),
  so nothing can be lost between "saved" and "queued".
- `claim_next` uses `FOR UPDATE SKIP LOCKED`, so several workers can run without
  ever taking the same job.
- Failures are retried with backoff up to `job_max_attempts`; after that the
  case goes to a person as "Pipeline error" (fail closed).
- A job left "running" by a crashed worker is reclaimed after `job_stale_seconds`.
"""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.config import get_settings
from returnguard.models import Job, JobStatus

log = structlog.get_logger(__name__)

REVIEW_JOB = "review_return"


async def claim_next(db: AsyncSession) -> Job | None:
    """Take the next due job (or an abandoned one) and mark it running. Commits."""
    settings = get_settings()
    now = datetime.now(UTC)
    job = await db.scalar(
        select(Job)
        .where(
            or_(
                and_(Job.status == JobStatus.QUEUED, Job.run_after <= now),
                and_(
                    Job.status == JobStatus.RUNNING,
                    Job.locked_at < now - timedelta(seconds=settings.job_stale_seconds),
                ),
            )
        )
        .order_by(Job.run_after)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        await db.rollback()
        return None
    if job.status is JobStatus.RUNNING:
        log.warning("jobs.reclaimed_stale", job_id=str(job.id), attempts=job.attempts)
    job.status = JobStatus.RUNNING
    job.locked_at = now
    job.attempts += 1
    await db.commit()
    return job


async def complete(db: AsyncSession, job_id: uuid.UUID) -> None:
    job = await db.get_one(Job, job_id)
    job.status = JobStatus.DONE
    job.locked_at = None
    job.last_error = None
    await db.commit()


async def fail(db: AsyncSession, job_id: uuid.UUID, error: str) -> bool:
    """Record a failure. Returns True if the job is out of attempts (now FAILED)."""
    settings = get_settings()
    job = await db.get_one(Job, job_id, populate_existing=True)
    job.last_error = error[:2000]
    job.locked_at = None
    if job.attempts >= settings.job_max_attempts:
        job.status = JobStatus.FAILED
        await db.commit()
        log.error("jobs.failed", job_id=str(job.id), attempts=job.attempts, error=error[:200])
        return True
    delays = settings.job_retry_seconds or (30,)
    delay = delays[min(job.attempts - 1, len(delays) - 1)]
    job.status = JobStatus.QUEUED
    job.run_after = datetime.now(UTC) + timedelta(seconds=delay)
    await db.commit()
    log.warning("jobs.retry_scheduled", job_id=str(job.id), attempt=job.attempts, delay_s=delay)
    return False


async def next_due_in(db: AsyncSession) -> float | None:
    """Seconds until the next queued job is due (0 if overdue), or None if none."""
    run_after = await db.scalar(
        select(func.min(Job.run_after)).where(Job.status == JobStatus.QUEUED)
    )
    await db.rollback()
    if run_after is None:
        return None
    return max(0.0, (run_after - datetime.now(UTC)).total_seconds())
