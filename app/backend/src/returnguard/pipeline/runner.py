"""Runs one return through the pipeline and applies the gate's decision.

Every step writes an `agent_runs` row (what ran, on what, with what result) and
`agent_run_events` (for the live trace), and the outcome goes to the audit log.
Steps that need customer details see only the masked `Case` (M8).
"""

import hashlib
import json
import random
import uuid
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from returnguard import audit
from returnguard.models import (
    ActorType,
    AgentRun,
    AgentRunEvent,
    DeciderType,
    Decision,
    EscalationReason,
    Order,
    OrderItem,
    PolicyDoc,
    Return,
    ReturnPhoto,
    ReturnStatus,
    Route,
    Settings,
    User,
)
from returnguard.pipeline.behavior import BehaviorInputs, BehaviorScore, score_behavior
from returnguard.pipeline.checks import data_check, policy_facts
from returnguard.pipeline.gate import GateInputs, GateSettings, governance_gate
from returnguard.pipeline.steps import Case, RuleSteps, Steps

log = structlog.get_logger(__name__)

# Statuses the pipeline may (re)start from. Anything else is already decided or
# with a person, so a duplicate or late job is a no-op.
RUNNABLE = {ReturnStatus.SUBMITTED, ReturnStatus.CHECKING}


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


class Trace:
    """Records each step for the trace view and observability."""

    def __init__(self, db: AsyncSession, return_id: uuid.UUID, policy_version: int | None):
        self.db = db
        self.return_id = return_id
        self.run_id = uuid.uuid4()
        self.policy_version = policy_version

    def event(self, step: str, kind: str, data: dict[str, Any] | None = None) -> None:
        self.db.add(
            AgentRunEvent(
                return_id=self.return_id,
                run_id=self.run_id,
                step=step,
                kind=kind,
                data=_jsonable(data or {}),
            )
        )

    def step(
        self, step: str, inputs: Any, output: Any, *, latency_ms: int, model: str | None = None
    ) -> None:
        payload = json.dumps(_jsonable(inputs), sort_keys=True).encode()
        self.db.add(
            AgentRun(
                return_id=self.return_id,
                run_id=self.run_id,
                step=step,
                model=model,
                policy_version=self.policy_version,
                input_hash=hashlib.sha256(payload).hexdigest(),
                output=_jsonable(output),
                latency_ms=latency_ms,
            )
        )
        self.event(step, "finished", {"latency_ms": latency_ms})


async def _behavior_inputs(
    db: AsyncSession, ret: Return, order: Order, customer: User, high_value_limit: int
) -> BehaviorInputs:
    now = datetime.now(UTC)
    past_orders = await db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.customer_id == customer.id, Order.id != order.id)
    )
    past_returns = await db.scalar(
        select(func.count())
        .select_from(Return)
        .where(Return.customer_id == customer.id, Return.id != ret.id)
    )
    recent = await db.scalar(
        select(func.count())
        .select_from(Return)
        .where(
            Return.customer_id == customer.id,
            Return.id != ret.id,
            Return.created_at >= now - timedelta(days=30),
        )
    )
    shared = await db.scalar(
        select(func.count(func.distinct(Order.customer_id))).where(
            Order.address_fingerprint == order.address_fingerprint,
            Order.customer_id != customer.id,
        )
    )
    return BehaviorInputs(
        past_orders=past_orders or 0,
        past_returns=past_returns or 0,
        recent_returns_30d=recent or 0,
        account_age_days=max(0, (now - customer.created_at).days),
        other_accounts_at_address=shared or 0,
        refund_cents=ret.refund_amount_cents,
        high_value_limit_cents=high_value_limit,
    )


def _ms(start: datetime) -> int:
    return int((datetime.now(UTC) - start).total_seconds() * 1000)


async def review_return(
    db: AsyncSession,
    return_id: uuid.UUID,
    *,
    steps: Steps | None = None,
    rng: random.Random | None = None,
) -> ReturnStatus | None:
    """Review one return. Commits its own progress. Returns the new status, or None if skipped."""
    steps = steps or RuleSteps()
    ret = await db.scalar(
        select(Return)
        .where(Return.id == return_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if ret is None or ret.status not in RUNNABLE:
        await db.rollback()
        return None

    item = await db.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(selectinload(OrderItem.product), selectinload(OrderItem.order))
    )
    assert item is not None
    order, product = item.order, item.product
    customer = await db.get_one(User, ret.customer_id)
    photos = list(await db.scalars(select(ReturnPhoto).where(ReturnPhoto.return_id == ret.id)))
    settings = await db.get_one(Settings, 1)
    policy = await db.scalar(select(PolicyDoc).where(PolicyDoc.is_active))
    policy_version = policy.version if policy else None

    trace = Trace(db, ret.id, policy_version)
    ret.status = ReturnStatus.CHECKING
    trace.event("pipeline", "started", {"reason": ret.reason.value})
    await db.commit()  # the customer now sees "Being checked"

    # 1. Data check (code). Missing evidence goes back to the customer (M6).
    t = datetime.now(UTC)
    dc = data_check(
        reason=ret.reason, photo_count=len(photos), delivered=order.delivered_at is not None
    )
    trace.step("data_check", {"reason": ret.reason, "photos": len(photos)}, dc, latency_ms=_ms(t))
    if not dc.complete:
        ret.status = ReturnStatus.NEEDS_INFO
        ret.route = Route.CUSTOMER
        ret.customer_message = dc.customer_message
        ret.policy_version = policy_version
        audit.record(
            db,
            actor_type=ActorType.CHECK,
            action="check.missing_evidence",
            return_id=ret.id,
            details={"missing": dc.missing},
        )
        await db.commit()
        log.info("pipeline.needs_info", case_number=ret.case_number, missing=dc.missing)
        return ret.status
    assert order.delivered_at is not None

    # Policy facts (code): window, Final Sale, high value.
    facts = policy_facts(
        reason=ret.reason,
        delivered_at=order.delivered_at,
        requested_at=ret.created_at,
        is_final_sale=product.is_final_sale,
        refund_cents=ret.refund_amount_cents,
        high_value_limit_cents=settings.high_value_limit_cents,
    )
    case = Case(
        reason=ret.reason,
        reason_text=ret.reason_text,
        product_name=product.name,
        product_category=product.category.value,
        is_final_sale=product.is_final_sale,
        refund_cents=ret.refund_amount_cents,
        photo_keys=[p.storage_key for p in photos],
        policy_version=policy_version or 0,
    )

    # 2-3. Policy and photo.
    t = datetime.now(UTC)
    policy_result = await steps.policy(case, facts)
    trace.step("policy", {"facts": facts, "reason": ret.reason}, policy_result, latency_ms=_ms(t))
    t = datetime.now(UTC)
    photo_result = await steps.photo(case, facts)
    trace.step("image", {"photos": len(photos)}, photo_result, latency_ms=_ms(t))

    # 4. Behaviour risk (code).
    t = datetime.now(UTC)
    behavior: BehaviorScore = score_behavior(
        await _behavior_inputs(db, ret, order, customer, settings.high_value_limit_cents)
    )
    trace.step("behavior", {"customer": "masked"}, behavior, latency_ms=_ms(t))

    # 5-6. Recommendation and critic.
    t = datetime.now(UTC)
    rec = await steps.recommend(case, facts, policy_result, photo_result, behavior)
    trace.step("recommendation", {"policy": policy_result.eligibility}, rec, latency_ms=_ms(t))
    t = datetime.now(UTC)
    critic = await steps.critic(case, policy_result, photo_result, rec)
    trace.step("critic", {"proposal": rec.proposal}, critic, latency_ms=_ms(t))

    # 7. Governance gate (code): the only place a decision becomes final.
    gate = governance_gate(
        GateInputs(
            eligibility=policy_result.eligibility,
            photo=photo_result.check,
            proposal=rec.proposal,
            ambiguous=rec.ambiguous,
            critic_veto=critic.veto,
            risk_score=behavior.score,
            refund_cents=ret.refund_amount_cents,
        ),
        GateSettings(
            automation_enabled=settings.automation_enabled,
            risk_limit=settings.risk_limit,
            high_value_limit_cents=settings.high_value_limit_cents,
            qa_sample_rate=settings.qa_sample_rate,
        ),
        rng=rng,
    )
    trace.step("gate", {"proposal": rec.proposal, "risk": behavior.score}, gate, latency_ms=0)

    ret.ai_proposal = rec.proposal
    ret.evidence_strength = gate.evidence_strength
    ret.route = gate.route
    ret.escalation_reason = gate.escalation_reason
    ret.policy_version = policy_version
    if gate.auto_approved:
        ret.status = ReturnStatus.APPROVED
        ret.final_decision = Decision.APPROVE
        ret.decided_by_type = DeciderType.AUTO
        ret.decided_at = datetime.now(UTC)
        clauses = ", ".join(policy_result.cited_clauses)
        ret.customer_message = (
            f"Your return was approved automatically under policy {clauses} "
            f"(version {policy_version}). Your refund will be issued to your original "
            "payment method within 5 to 7 business days (P9)."
        )
    else:
        ret.status = ReturnStatus.UNDER_REVIEW
    audit.record(
        db,
        actor_type=ActorType.GATE,
        action="gate.auto_approved" if gate.auto_approved else "gate.escalated",
        return_id=ret.id,
        details={
            "route": gate.route.value,
            "reasons": [r.value for r in gate.reasons],
            "evidence_strength": gate.evidence_strength.value,
            "proposal": rec.proposal.value,
            "risk_score": behavior.score,
            "steps_source": getattr(steps, "source", "unknown"),
        },
    )
    trace.event("pipeline", "finished", {"status": ret.status.value})
    await db.commit()
    log.info(
        "pipeline.decided",
        case_number=ret.case_number,
        status=ret.status.value,
        reason=gate.escalation_reason.value if gate.escalation_reason else None,
    )
    return ret.status


async def mark_pipeline_failed(db: AsyncSession, return_id: uuid.UUID, error: str) -> None:
    """After the last retry: send the case to a person (fail closed)."""
    ret = await db.get(Return, return_id)
    if ret is None or ret.status not in RUNNABLE:
        return
    ret.status = ReturnStatus.FAILED
    ret.route = Route.REVIEWER
    ret.escalation_reason = EscalationReason.PIPELINE_ERROR
    audit.record(
        db,
        actor_type=ActorType.SYSTEM,
        action="pipeline.failed",
        return_id=ret.id,
        details={"error": error[:500]},
    )
    await db.commit()
