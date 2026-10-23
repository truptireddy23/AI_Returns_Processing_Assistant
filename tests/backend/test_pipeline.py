"""The review pipeline end to end on a real database, with the rule-based steps."""

import random
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import db, jobs, worker
from returnguard.models import (
    AgentRun,
    AuditLog,
    DeciderType,
    Decision,
    EscalationReason,
    EvidenceStrength,
    Job,
    JobStatus,
    Order,
    Return,
    ReturnPhoto,
    ReturnReason,
    ReturnStatus,
    Route,
    Settings,
    User,
)
from returnguard.pipeline.runner import review_return
from returnguard.pipeline.steps import RuleSteps

from . import images
from .factories import PASSWORD, make_order, make_user

pytestmark = pytest.mark.db


class NoSample(random.Random):
    """QA sampling never picks the case (draw above any rate)."""

    def random(self) -> float:
        return 0.999


async def set_automation(session: AsyncSession, on: bool, qa: str = "0.10") -> None:
    settings = await session.get_one(Settings, 1)
    settings.automation_enabled = on
    settings.qa_sample_rate = Decimal(qa)
    await session.flush()


async def make_return(
    session: AsyncSession,
    *,
    customer: User | None = None,
    reason: ReturnReason = ReturnReason.CHANGED_MIND,
    photo: bool = False,
    delivered_days_ago: int = 5,
    price_cents: int = 8900,
    final_sale: bool = False,
) -> Return:
    customer = customer or await make_user(session)
    order = await make_order(session, customer, price_cents=price_cents)
    order.delivered_at = datetime.now(UTC) - timedelta(days=delivered_days_ago)
    product = (await session.get_one(Order, order.id)).items[0]
    item = order.items[0]
    if final_sale:
        from returnguard.models import Product

        p = await session.get_one(Product, product.product_id)
        p.is_final_sale = True
    ret = Return(
        order_item_id=item.id,
        customer_id=customer.id,
        reason=reason,
        refund_amount_cents=price_cents,
        status=ReturnStatus.SUBMITTED,
    )
    session.add(ret)
    await session.flush()
    if photo:
        session.add(
            ReturnPhoto(
                return_id=ret.id,
                storage_key=f"returns/{ret.id}/x.jpg",
                content_type="image/jpeg",
                size_bytes=10,
                sha256="0" * 64,
            )
        )
    session.add(Job(kind=jobs.REVIEW_JOB, return_id=ret.id))
    await session.flush()
    return ret


async def review(session: AsyncSession, ret: Return) -> Return:
    """Review as the worker would: run the pipeline, then mark the job done."""
    queued = list(
        await session.scalars(
            select(Job).where(Job.return_id == ret.id, Job.status == JobStatus.QUEUED)
        )
    )
    await review_return(session, ret.id, steps=RuleSteps(), rng=NoSample())
    for job in queued:
        job.status = JobStatus.DONE
    await session.flush()
    return await session.get_one(Return, ret.id, populate_existing=True)


# --- Outcomes ---------------------------------------------------------------


async def test_a_clear_change_of_mind_is_auto_approved_when_automation_is_on(
    db_session: AsyncSession,
) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session))

    assert ret.status is ReturnStatus.APPROVED
    assert ret.route is Route.AUTO_APPROVED
    assert ret.final_decision is Decision.APPROVE
    assert ret.decided_by_type is DeciderType.AUTO
    assert ret.evidence_strength is EvidenceStrength.STRONG
    assert ret.customer_message is not None and "approved automatically" in ret.customer_message
    assert "P5" in ret.customer_message


async def test_with_automation_off_the_ai_only_recommends(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))

    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.AUTOMATION_OFF
    assert ret.ai_proposal is Decision.APPROVE  # recorded for agreement tracking (shadow mode)
    assert ret.final_decision is None


async def test_a_missing_photo_goes_back_to_the_customer(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session, reason=ReturnReason.DAMAGED))

    assert ret.status is ReturnStatus.NEEDS_INFO
    assert ret.route is Route.CUSTOMER
    assert ret.escalation_reason is None  # never a queue reason (M6)
    assert ret.customer_message == "We need a photo of the problem to continue."
    audit = await db_session.scalar(
        select(AuditLog).where(
            AuditLog.return_id == ret.id, AuditLog.action == "check.missing_evidence"
        )
    )
    assert audit is not None


async def test_a_late_return_is_a_proposed_denial_for_a_person(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session, delivered_days_ago=47))

    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.PROPOSED_DENIAL
    assert ret.ai_proposal is Decision.DENY
    assert ret.final_decision is None  # the AI can never deny (M1)
    assert ret.evidence_strength is EvidenceStrength.WEAK


async def test_final_sale_change_of_mind_is_a_proposed_denial(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session, final_sale=True))
    assert ret.escalation_reason is EscalationReason.PROPOSED_DENIAL


async def test_photos_are_unverified_until_the_photo_check_exists(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    ret = await review(
        db_session, await make_return(db_session, reason=ReturnReason.DEFECTIVE, photo=True)
    )
    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.UNVERIFIED_PHOTO


async def test_high_value_always_goes_to_a_person(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session, price_cents=32900))
    assert ret.escalation_reason is EscalationReason.HIGH_VALUE


async def test_a_high_return_rate_is_elevated_risk(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True)
    customer = await make_user(db_session)
    customer.created_at = datetime.now(UTC) - timedelta(days=400)
    for i in range(8):
        order = await make_order(db_session, customer)
        if i < 5:
            db_session.add(
                Return(
                    order_item_id=order.items[0].id,
                    customer_id=customer.id,
                    reason=ReturnReason.CHANGED_MIND,
                    refund_amount_cents=8900,
                    status=ReturnStatus.APPROVED,
                    created_at=datetime.now(UTC) - timedelta(days=60 + i),
                )
            )
    await db_session.flush()

    ret = await review(db_session, await make_return(db_session, customer=customer))

    assert ret.escalation_reason is EscalationReason.ELEVATED_RISK


async def test_qa_sampling_sends_a_clear_case_to_a_person(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=True, qa="1.00")
    ret = await review(db_session, await make_return(db_session))
    assert ret.escalation_reason is EscalationReason.QA_SAMPLE


# --- Trace, audit, idempotency ---------------------------------------------


async def test_every_step_is_traced_and_the_decision_audited(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))

    steps = (
        await db_session.scalars(
            select(AgentRun.step).where(AgentRun.return_id == ret.id).order_by(AgentRun.created_at)
        )
    ).all()
    assert set(steps) == {
        "data_check",
        "policy",
        "image",
        "behavior",
        "recommendation",
        "critic",
        "gate",
    }
    gate_audit = await db_session.scalar(
        select(AuditLog).where(AuditLog.return_id == ret.id, AuditLog.action == "gate.escalated")
    )
    assert gate_audit is not None
    assert gate_audit.details["reasons"] == ["automation_off"]
    assert gate_audit.details["steps_source"] == "rules"


async def test_reviewing_twice_is_a_no_op(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=False)
    ret_id = (await review(db_session, await make_return(db_session))).id
    again = await review_return(db_session, ret_id, steps=RuleSteps())
    assert again is None
    assert (await db_session.get_one(Return, ret_id, populate_existing=True)).status is (
        ReturnStatus.UNDER_REVIEW
    )


# --- Jobs and the worker ----------------------------------------------------


@pytest.fixture
def worker_uses_test_session(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session

    monkeypatch.setattr(db, "get_session", _session)


@pytest.mark.usefixtures("worker_uses_test_session")
async def test_the_worker_processes_a_queued_job(db_session: AsyncSession) -> None:
    await set_automation(db_session, on=False)
    ret = await make_return(db_session)

    assert await worker.process_one(RuleSteps(), NoSample()) is True

    job = await db_session.scalar(select(Job).where(Job.return_id == ret.id))
    assert job is not None and job.status is JobStatus.DONE and job.attempts == 1
    assert (await db_session.get_one(Return, ret.id, populate_existing=True)).status is (
        ReturnStatus.UNDER_REVIEW
    )
    assert await worker.process_one(RuleSteps()) is False  # nothing left


class Broken(RuleSteps):
    async def policy(self, *_: object, **__: object):  # type: ignore[no-untyped-def]
        raise RuntimeError("model unavailable")


@pytest.mark.usefixtures("worker_uses_test_session")
async def test_failures_retry_then_go_to_a_person(db_session: AsyncSession) -> None:
    ret = await make_return(db_session)
    job = await db_session.scalar(select(Job).where(Job.return_id == ret.id))
    assert job is not None

    for attempt in (1, 2, 3):
        job.run_after = datetime.now(UTC) - timedelta(seconds=1)  # make the retry due now
        await db_session.flush()
        assert await worker.process_one(Broken()) is True
        job = await db_session.get_one(Job, job.id, populate_existing=True)
        assert job.attempts == attempt
        assert job.last_error is not None and "model unavailable" in job.last_error

    assert job.status is JobStatus.FAILED
    ret = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert ret.status is ReturnStatus.FAILED
    assert ret.route is Route.REVIEWER
    assert ret.escalation_reason is EscalationReason.PIPELINE_ERROR


async def test_retries_back_off(db_session: AsyncSession) -> None:
    ret = await make_return(db_session)
    job = await jobs.claim_next(db_session)
    assert job is not None and job.return_id == ret.id

    out_of_attempts = await jobs.fail(db_session, job.id, "boom")

    job = await db_session.get_one(Job, job.id, populate_existing=True)
    assert not out_of_attempts
    assert job.status is JobStatus.QUEUED
    assert job.run_after > datetime.now(UTC) + timedelta(seconds=20)
    assert await jobs.claim_next(db_session) is None  # not due yet
    due = await jobs.next_due_in(db_session)
    assert due is not None and 20 < due <= 30


async def test_an_abandoned_running_job_is_reclaimed(db_session: AsyncSession) -> None:
    ret = await make_return(db_session)
    job = await db_session.scalar(select(Job).where(Job.return_id == ret.id))
    assert job is not None
    job.status = JobStatus.RUNNING
    job.locked_at = datetime.now(UTC) - timedelta(hours=1)
    job.attempts = 1
    await db_session.flush()

    claimed = await jobs.claim_next(db_session)

    assert claimed is not None and claimed.id == job.id and claimed.attempts == 2


# --- The customer adds the missing photo -------------------------------------


async def test_adding_the_missing_photo_queues_another_review(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    customer = await make_user(db_session)
    ret = await review(
        db_session, await make_return(db_session, customer=customer, reason=ReturnReason.DAMAGED)
    )
    assert ret.status is ReturnStatus.NEEDS_INFO
    login = await db_client.post(
        "/api/auth/login", json={"email": customer.email, "password": PASSWORD}
    )
    db_client.headers["X-CSRF-Token"] = login.json()["csrf_token"]

    res = await db_client.post(
        f"/api/returns/{ret.id}/photos", files={"photo": ("p.jpg", images.jpeg(), "image/jpeg")}
    )

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "submitted" and len(res.json()["photos"]) == 1
    queued = (
        await db_session.scalars(
            select(Job).where(Job.return_id == ret.id, Job.status == JobStatus.QUEUED)
        )
    ).all()
    assert len(queued) == 1

    # Reviewing again now reaches the photo step (and, until M6, a person).
    ret = await review(db_session, ret)
    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.UNVERIFIED_PHOTO

    # Only while the return is waiting for a photo, and only for its owner.
    again = await db_client.post(
        f"/api/returns/{ret.id}/photos", files={"photo": ("p.jpg", images.jpeg(), "image/jpeg")}
    )
    assert again.status_code == 409
    stranger = await make_user(db_session)
    login = await db_client.post(
        "/api/auth/login", json={"email": stranger.email, "password": PASSWORD}
    )
    db_client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    other = await db_client.post(
        f"/api/returns/{uuid.uuid4()}/photos",
        files={"photo": ("p.jpg", images.jpeg(), "image/jpeg")},
    )
    assert other.status_code == 404
