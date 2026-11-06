"""A reviewer re-running the AI checks on a case already with a person.

For cases first checked without a model (or that hit a pipeline error): the fresh run
replaces what the case page shows, but the case stays with the reviewer and is never
decided by it.
"""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import db, jobs, worker
from returnguard.models import (
    AgentRun,
    AuditLog,
    EscalationReason,
    Job,
    JobStatus,
    Return,
    ReturnReason,
    ReturnStatus,
    Role,
    Route,
    User,
)
from returnguard.pipeline.runner import review_return
from returnguard.pipeline.steps import RuleSteps
from returnguard.routers import review as review_router

from .factories import make_user
from .test_pipeline import NoSample, make_return, set_automation
from .test_review import ensure_policy, escalated_case, signed_in

pytestmark = pytest.mark.db


@pytest.fixture
def model_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(review_router, "_model_configured", lambda: True)


@pytest.fixture
def worker_uses_test_session(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr(db, "get_session", _session)


async def rerun(client: httpx.AsyncClient, headers: dict[str, str], ret: Return) -> httpx.Response:
    return await client.post(f"/api/review/cases/{ret.id}/rerun", headers=headers)


async def runs(session: AsyncSession, ret: Return) -> int:
    count = await session.scalar(
        select(func.count(func.distinct(AgentRun.run_id))).where(AgentRun.return_id == ret.id)
    )
    return count or 0


# --- The endpoint -----------------------------------------------------------


async def test_without_a_model_there_is_nothing_to_rerun(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    headers = await signed_in(db_client, await make_user(db_session, role=Role.REVIEWER))

    case = (await db_client.get(f"/api/review/cases/{ret.id}", headers=headers)).json()
    assert case["can_rerun"] is False
    assert "No AI model is configured" in case["cannot_rerun_reason"]
    assert (await rerun(db_client, headers, ret)).status_code == 409


@pytest.mark.usefixtures("model_configured")
async def test_a_reviewer_queues_a_rerun_once(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, role=Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    res = await rerun(db_client, headers, ret)

    assert res.status_code == 200, res.text
    assert res.json()["rerun_pending"] is True
    assert res.json()["can_rerun"] is False
    assert res.json()["status"] == "under_review"
    job = await db_session.scalar(
        select(Job).where(Job.return_id == ret.id, Job.kind == jobs.RERUN_JOB)
    )
    assert job is not None and job.status is JobStatus.QUEUED
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.return_id == ret.id, AuditLog.action == "review.rerun_requested"
        )
    )
    assert audit is not None and audit.actor_user_id == reviewer.id

    again = await rerun(db_client, headers, ret)
    assert again.status_code == 409
    assert "already re-running" in again.json()["detail"]


@pytest.mark.usefixtures("model_configured")
async def test_customers_cannot_rerun(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    headers = await signed_in(db_client, customer)

    assert (await rerun(db_client, headers, ret)).status_code == 403


@pytest.mark.usefixtures("model_configured")
async def test_not_while_another_reviewer_has_the_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    other = await make_user(db_session, role=Role.REVIEWER)
    ret.claimed_by_user_id, ret.claimed_at = other.id, datetime.now(UTC)
    await db_session.flush()
    headers = await signed_in(db_client, await make_user(db_session, role=Role.REVIEWER))

    res = await rerun(db_client, headers, ret)
    assert res.status_code == 409
    assert "Another reviewer" in res.json()["detail"]


@pytest.mark.usefixtures("model_configured")
async def test_not_once_the_case_is_decided(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    ret.status = ReturnStatus.APPROVED
    await db_session.flush()
    headers = await signed_in(db_client, await make_user(db_session, role=Role.REVIEWER))

    assert (await rerun(db_client, headers, ret)).status_code == 409


# --- The pipeline in re-run mode --------------------------------------------


async def test_a_rerun_never_decides_and_keeps_the_claim(db_session: AsyncSession) -> None:
    """A clear change of mind would be auto-approved with automation on; on a re-run
    it stays with the reviewer who has it, with a fresh run on record."""
    await ensure_policy(db_session)
    await set_automation(db_session, False, qa="0")
    ret = await make_return(db_session, reason=ReturnReason.CHANGED_MIND)
    await review_return(db_session, ret.id, steps=RuleSteps(), rng=NoSample())
    ret = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert ret.status is ReturnStatus.UNDER_REVIEW
    reviewer = await make_user(db_session, role=Role.REVIEWER)
    ret.claimed_by_user_id, ret.claimed_at = reviewer.id, datetime.now(UTC)
    await set_automation(db_session, True, qa="0")
    before = await runs(db_session, ret)

    status = await review_return(db_session, ret.id, steps=RuleSteps(), rng=NoSample(), rerun=True)

    ret = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert status is ReturnStatus.UNDER_REVIEW
    assert ret.status is ReturnStatus.UNDER_REVIEW and ret.final_decision is None
    assert ret.route is Route.REVIEWER
    assert ret.claimed_by_user_id == reviewer.id
    assert await runs(db_session, ret) == before + 1
    assert await db_session.scalar(
        select(AuditLog).where(AuditLog.return_id == ret.id, AuditLog.action == "gate.rerun")
    )


async def test_a_rerun_brings_a_failed_case_back_under_review(db_session: AsyncSession) -> None:
    ret = await escalated_case(db_session)
    ret.status = ReturnStatus.FAILED
    ret.escalation_reason = EscalationReason.PIPELINE_ERROR
    await db_session.flush()

    await review_return(db_session, ret.id, steps=RuleSteps(), rng=NoSample(), rerun=True)

    ret = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.UNVERIFIED_PHOTO


async def test_a_rerun_skips_a_case_that_is_already_decided(db_session: AsyncSession) -> None:
    ret = await escalated_case(db_session)
    ret.status = ReturnStatus.APPROVED
    await db_session.commit()  # a skipped run rolls back; the case must already be saved
    ret_id, before = ret.id, await runs(db_session, ret)

    assert await review_return(db_session, ret_id, steps=RuleSteps(), rerun=True) is None
    ret = await db_session.get_one(Return, ret_id, populate_existing=True)
    assert ret.status is ReturnStatus.APPROVED
    assert await runs(db_session, ret) == before


class Broken(RuleSteps):
    async def policy(self, *_: object, **__: object):  # type: ignore[no-untyped-def]
        raise RuntimeError("model unavailable")


@pytest.mark.usefixtures("worker_uses_test_session")
async def test_a_failed_rerun_leaves_the_case_with_the_reviewer(db_session: AsyncSession) -> None:
    ret = await escalated_case(db_session)
    ret_id = ret.id
    job = Job(kind=jobs.RERUN_JOB, return_id=ret_id)
    db_session.add(job)
    await db_session.flush()
    job_id = job.id

    for _ in range(3):
        job = await db_session.get_one(Job, job_id, populate_existing=True)
        job.run_after = datetime.now(UTC) - timedelta(seconds=1)
        await db_session.flush()
        assert await worker.process_one(Broken()) is True

    job = await db_session.get_one(Job, job_id, populate_existing=True)
    assert job.status is JobStatus.FAILED
    ret = await db_session.get_one(Return, ret_id, populate_existing=True)
    assert ret.status is ReturnStatus.UNDER_REVIEW  # not FAILED: a person already has it
    assert await db_session.scalar(
        select(AuditLog).where(
            AuditLog.return_id == ret.id, AuditLog.action == "pipeline.rerun_failed"
        )
    )
