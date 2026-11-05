"""Reviewer: the queue of cases that need a person, and deciding them (M7).

The decide endpoint is the one place a case actually gets approved or denied
by a human. It never lets a reviewer approve or deny on behalf of the AI —
`decision` must be an explicit choice — and it writes the same audit trail
and agreement-sample record regardless of whether the reviewer agreed with
the AI's proposal or overrode it (S1).
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard import audit
from returnguard.auth import DbSession, require_role
from returnguard.models import (
    AgentRun,
    AgreementKind,
    AgreementSample,
    DeciderType,
    Decision,
    EscalationReason,
    EvidenceStrength,
    OrderItem,
    Return,
    ReturnPhoto,
    ReturnReason,
    ReturnStatus,
    ReviewRequest,
    ReviewRequestStatus,
    Role,
    Settings,
    User,
)
from returnguard.pipeline.runner import _behavior_inputs

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])

# Admins hold every reviewer right (DESIGN_SPEC.md decision-rights table).
Reviewer = Annotated[User, Depends(require_role(Role.REVIEWER, Role.ADMIN))]

DECIDABLE = {ReturnStatus.UNDER_REVIEW, ReturnStatus.FAILED}


class QueueItem(BaseModel):
    id: str
    case_number: int
    refund_amount_cents: int
    ai_proposal: Decision | None
    escalation_reason: EscalationReason | None
    created_at: datetime


@router.get("/queue", response_model=list[QueueItem])
async def queue(_: Reviewer, db: DbSession) -> list[QueueItem]:
    rows = await db.scalars(
        select(Return)
        .where(Return.status.in_([ReturnStatus.UNDER_REVIEW, ReturnStatus.FAILED]))
        .order_by(Return.created_at)
    )
    return [
        QueueItem(
            id=str(r.id),
            case_number=r.case_number,
            refund_amount_cents=r.refund_amount_cents,
            ai_proposal=r.ai_proposal,
            escalation_reason=r.escalation_reason,
            created_at=r.created_at,
        )
        for r in rows
    ]


# --- Case detail --------------------------------------------------------


class PhotoOut(BaseModel):
    id: str
    url: str


class FindingOut(BaseModel):
    """One pipeline step's result, from its most recent run (`agent_runs`).

    `output` is the step's own result dict (e.g. the Policy step's cited
    clauses, the Image step's authenticity notes) — deliberately untyped here
    so the case page can render whatever a step actually produced, rules-based
    or model-based, without this schema needing to change per step.
    """

    step: str
    model: str | None
    source: str | None
    output: dict[str, Any]


class CustomerHistoryOut(BaseModel):
    account_age_days: int
    past_orders: int
    past_returns: int
    recent_returns_30d: int
    other_accounts_at_address: int


class ReviewRequestOut(BaseModel):
    customer_explanation: str
    status: ReviewRequestStatus
    created_at: datetime


class CaseDetailOut(BaseModel):
    id: str
    case_number: int
    order_number: int
    product_name: str
    product_photo_url: str | None
    reason: ReturnReason
    reason_text: str
    refund_amount_cents: int
    status: ReturnStatus
    ai_proposal: Decision | None
    evidence_strength: EvidenceStrength | None
    escalation_reason: EscalationReason | None
    policy_version: int | None
    photos: list[PhotoOut]
    findings: list[FindingOut]
    customer_history: CustomerHistoryOut
    final_decision: Decision | None
    decided_by_type: str | None
    decided_by_user_id: str | None
    review_request: ReviewRequestOut | None
    created_at: datetime


async def _latest_findings(db: DbSession, return_id: uuid.UUID) -> list[FindingOut]:
    """The most recent pipeline run's steps, in pipeline order."""
    latest_run_id = await db.scalar(
        select(AgentRun.run_id)
        .where(AgentRun.return_id == return_id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    if latest_run_id is None:
        return []
    order = {
        "data_check": 0,
        "policy": 1,
        "image": 2,
        "behavior": 3,
        "recommendation": 4,
        "critic": 5,
        "gate": 6,
    }
    rows = list(
        await db.scalars(
            select(AgentRun).where(AgentRun.run_id == latest_run_id).order_by(AgentRun.created_at)
        )
    )
    rows.sort(key=lambda r: order.get(r.step, 99))
    return [
        FindingOut(
            step=r.step,
            model=r.model,
            source=(r.output or {}).get("source") if isinstance(r.output, dict) else None,
            output=r.output or {},
        )
        for r in rows
    ]


async def _case_detail(db: DbSession, return_id: uuid.UUID) -> CaseDetailOut:
    ret = await db.scalar(
        select(Return).where(Return.id == return_id).execution_options(populate_existing=True)
    )
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    item = await db.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(selectinload(OrderItem.product), selectinload(OrderItem.order))
    )
    assert item is not None
    photos = list(
        await db.scalars(
            select(ReturnPhoto)
            .where(ReturnPhoto.return_id == ret.id)
            .order_by(ReturnPhoto.created_at)
        )
    )
    customer = await db.get_one(User, ret.customer_id)
    settings = await db.get_one(Settings, 1)
    behavior_inputs = await _behavior_inputs(
        db, ret, item.order, customer, settings.high_value_limit_cents
    )
    review_request = await db.scalar(select(ReviewRequest).where(ReviewRequest.return_id == ret.id))

    return CaseDetailOut(
        id=str(ret.id),
        case_number=ret.case_number,
        order_number=item.order.order_number,
        product_name=item.product.name,
        product_photo_url=item.product.photo_key,
        reason=ret.reason,
        reason_text=ret.reason_text,
        refund_amount_cents=ret.refund_amount_cents,
        status=ret.status,
        ai_proposal=ret.ai_proposal,
        evidence_strength=ret.evidence_strength,
        escalation_reason=ret.escalation_reason,
        policy_version=ret.policy_version,
        photos=[PhotoOut(id=str(p.id), url=f"/api/returns/{ret.id}/photos/{p.id}") for p in photos],
        findings=await _latest_findings(db, ret.id),
        customer_history=CustomerHistoryOut(
            account_age_days=behavior_inputs.account_age_days,
            past_orders=behavior_inputs.past_orders,
            past_returns=behavior_inputs.past_returns,
            recent_returns_30d=behavior_inputs.recent_returns_30d,
            other_accounts_at_address=behavior_inputs.other_accounts_at_address,
        ),
        final_decision=ret.final_decision,
        decided_by_type=ret.decided_by_type.value if ret.decided_by_type else None,
        decided_by_user_id=str(ret.decided_by_user_id) if ret.decided_by_user_id else None,
        review_request=(
            ReviewRequestOut(
                customer_explanation=review_request.customer_explanation,
                status=review_request.status,
                created_at=review_request.created_at,
            )
            if review_request is not None
            else None
        ),
        created_at=ret.created_at,
    )


@router.get("/{return_id}", response_model=CaseDetailOut)
async def get_case(return_id: uuid.UUID, _: Reviewer, db: DbSession) -> CaseDetailOut:
    return await _case_detail(db, return_id)


# --- Decide ---------------------------------------------------------------


class DecideRequest(BaseModel):
    decision: Decision
    override_reason: str | None = None


def _policy_clauses(findings: list[FindingOut]) -> list[str]:
    for f in findings:
        if f.step == "policy":
            clauses = f.output.get("cited_clauses")
            if isinstance(clauses, list):
                return [c for c in clauses if isinstance(c, str)]
    return []


@router.post("/{return_id}/decide", response_model=CaseDetailOut)
async def decide(
    return_id: uuid.UUID, body: DecideRequest, user: Reviewer, db: DbSession
) -> CaseDetailOut:
    if body.decision not in (Decision.APPROVE, Decision.DENY):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose approve or deny.")

    ret = await db.scalar(
        select(Return)
        .where(Return.id == return_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    if ret.status not in DECIDABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This case isn't waiting for a decision.")

    review_request = await db.scalar(
        select(ReviewRequest).where(
            ReviewRequest.return_id == ret.id, ReviewRequest.status == ReviewRequestStatus.OPEN
        )
    )
    if review_request is not None and review_request.original_decider_id == user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "A different reviewer must handle a case the customer asked to have reviewed again.",
        )

    disagreed = body.decision != ret.ai_proposal
    if disagreed and not (body.override_reason or "").strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Tell us why you disagree with the AI's recommendation.",
        )

    findings = await _latest_findings(db, ret.id)
    now = datetime.now(UTC)
    ret.final_decision = body.decision
    ret.decided_by_type = DeciderType.PERSON
    ret.decided_by_user_id = user.id
    ret.decided_at = now
    ret.status = ReturnStatus.APPROVED if body.decision is Decision.APPROVE else ReturnStatus.DENIED

    if body.decision is Decision.APPROVE:
        clauses = ", ".join(_policy_clauses(findings)) or "the applicable policy"
        ret.customer_message = (
            f"Your return was approved under policy {clauses} (version {ret.policy_version}). "
            "This decision was reviewed by a member of our team. Your refund will be issued "
            "to your original payment method within 5 to 7 business days (P9)."
        )
    else:
        ret.customer_message = (
            "Your return was not approved. This decision was reviewed by a member of our team. "
            + (f"Reason: {body.override_reason.strip()}" if body.override_reason else "")
        ).strip()

    if ret.ai_proposal is not None:
        db.add(
            AgreementSample(
                return_id=ret.id,
                reviewer_id=user.id,
                kind=AgreementKind.OVERRIDE if disagreed else AgreementKind.AGREEMENT,
                ai_proposal=ret.ai_proposal,
                human_decision=body.decision,
                agreed=not disagreed,
            )
        )

    if review_request is not None:
        review_request.status = ReviewRequestStatus.RESOLVED
        review_request.assigned_reviewer_id = user.id
        review_request.outcome = body.decision
        review_request.resolved_at = now

    audit.record(
        db,
        actor_type=audit.actor_for_role(user.role),
        actor_user_id=user.id,
        action=f"review.{body.decision.value}",
        return_id=ret.id,
        details={
            "ai_proposal": ret.ai_proposal.value if ret.ai_proposal else None,
            "overrode_ai": disagreed,
            "override_reason": body.override_reason,
            "review_request_resolved": review_request is not None,
        },
    )
    await db.commit()
    log.info(
        "review.decided",
        case_number=ret.case_number,
        decision=body.decision.value,
        overrode_ai=disagreed,
    )
    return await _case_detail(db, ret.id)
