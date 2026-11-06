"""Reviewer: the queue, the case page, and the human decision (M7).

Rules enforced here, not just in the UI:
- Only reviewers and admins can see or decide cases.
- A case is decided once, by a person; a denial needs an explicit confirmation and
  the policy clause it rests on (M1, M7).
- Disagreeing with the AI's approve/deny proposal needs a predefined reason; every
  decision on such a case is recorded as an agreement sample (S1).
- A claim stops two reviewers working the same case; claims go stale after
  `CLAIM_TTL` so an abandoned tab can't lock a case forever.
- A customer's review request is decided by a different reviewer from the one who
  made the denial (S2; also a database CHECK).

The customer's name and email are never sent to the case page: the reviewer judges
the return and the account's behaviour, not the person (bias safeguard, M8).
"""

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import aliased, selectinload

from returnguard import audit, jobs
from returnguard.auth import DbSession, require_role
from returnguard.config import get_settings
from returnguard.models import (
    AgentRun,
    AgreementKind,
    AgreementSample,
    AuditLog,
    DeciderType,
    Decision,
    EscalationReason,
    EvidenceStrength,
    Job,
    JobStatus,
    Order,
    OrderItem,
    PolicyDoc,
    Product,
    ProductCategory,
    Return,
    ReturnPhoto,
    ReturnReason,
    ReturnStatus,
    ReviewRequest,
    ReviewRequestStatus,
    Role,
    Route,
    Settings,
    User,
)
from returnguard.pipeline.checks import RETURN_WINDOW_DAYS, days_since_delivery, shop_date
from returnguard.pipeline.llm import model_client
from returnguard.pipeline.runner import behavior_inputs
from returnguard.routers.catalog import WITH_PHOTOS, main_photo_url
from returnguard.wake import nudge_worker

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])

# Admins hold every reviewer right (DESIGN_SPEC.md decision-rights table).
Reviewer = Annotated[User, Depends(require_role(Role.REVIEWER, Role.ADMIN))]

OPEN_STATUSES = (ReturnStatus.UNDER_REVIEW, ReturnStatus.FAILED)
CLAIM_TTL = timedelta(minutes=30)
MAX_NOTE_LENGTH = 500

REASON_LABELS = {
    ReturnReason.DAMAGED: "Arrived damaged",
    ReturnReason.DEFECTIVE: "Defective / stopped working",
    ReturnReason.WRONG_ITEM: "Wrong item sent",
    ReturnReason.NOT_AS_DESCRIBED: "Not as described",
    ReturnReason.CHANGED_MIND: "Changed my mind",
}


class OverrideReason(StrEnum):
    """One-click reasons for disagreeing with the AI (S1, S5)."""

    LOOKS_LIKE_DEFECT = "looks_like_defect"
    LOOKS_LIKE_WEAR = "looks_like_wear"
    PHOTO_UNCLEAR = "photo_unclear"
    PHOTO_NOT_GENUINE = "photo_not_genuine"
    POLICY_MISAPPLIED = "policy_misapplied"
    HISTORY_EXPLAINS = "history_explains"
    OTHER = "other"


def shown_reason(
    reason: EscalationReason | None, rr_status: ReviewRequestStatus | None
) -> EscalationReason | None:
    """Why the case is in front of a person now. An open review request comes first;
    the return row keeps the gate's original reason, so the metrics stay right."""
    if rr_status is ReviewRequestStatus.OPEN:
        return EscalationReason.CUSTOMER_REQUESTED_REVIEW
    return reason


def _claim_is_live(ret: Return, now: datetime) -> bool:
    return (
        ret.claimed_by_user_id is not None
        and ret.claimed_at is not None
        and now - ret.claimed_at < CLAIM_TTL
    )


# --- Queue ------------------------------------------------------------------


class QueueItem(BaseModel):
    id: str
    case_number: int
    product_name: str
    product_category: ProductCategory
    refund_amount_cents: int
    status: ReturnStatus
    ai_proposal: Decision | None
    escalation_reason: EscalationReason | None
    evidence_strength: EvidenceStrength | None
    review_requested: bool
    claimed_by_name: str | None
    claimed_by_me: bool
    final_decision: Decision | None
    decided_by_name: str | None
    decided_at: datetime | None
    created_at: datetime


@router.get("/queue", response_model=list[QueueItem])
async def queue(
    user: Reviewer,
    db: DbSession,
    view: Annotated[Literal["open", "decided_by_me", "decided"], Query()] = "open",
) -> list[QueueItem]:
    """`open`: every case waiting on a person. `decided_by_me`: every case I approved
    or denied, newest first. `decided`: the 50 most recent decisions made by people.

    A denial the customer asked to have reviewed is back in the queue, so it isn't
    a final decision and leaves `decided_by_me` until it's decided again."""
    now = datetime.now(UTC)
    claimer = aliased(User)
    decider = aliased(User)
    stmt = (
        select(Return, Product, claimer, decider)
        .join(OrderItem, OrderItem.id == Return.order_item_id)
        .join(Product, Product.id == OrderItem.product_id)
        .outerjoin(claimer, claimer.id == Return.claimed_by_user_id)
        .outerjoin(decider, decider.id == Return.decided_by_user_id)
    )
    if view in ("decided", "decided_by_me"):
        stmt = stmt.where(
            Return.status.in_([ReturnStatus.APPROVED, ReturnStatus.DENIED]),
            Return.decided_by_type == DeciderType.PERSON,
        ).order_by(Return.decided_at.desc())
        if view == "decided_by_me":
            stmt = stmt.where(Return.decided_by_user_id == user.id).limit(500)
        else:
            stmt = stmt.limit(50)
    else:
        stmt = stmt.where(Return.status.in_(OPEN_STATUSES)).order_by(Return.created_at)

    rows = (await db.execute(stmt)).all()
    requested = {
        return_id: rr_status
        for return_id, rr_status in await db.execute(
            select(ReviewRequest.return_id, ReviewRequest.status).where(
                ReviewRequest.return_id.in_([r.id for r, *_ in rows])
            )
        )
    }
    out = []
    for r, product, claim_user, decide_user in rows:
        live = _claim_is_live(r, now)
        out.append(
            QueueItem(
                id=str(r.id),
                case_number=r.case_number,
                product_name=product.name,
                product_category=product.category,
                refund_amount_cents=r.refund_amount_cents,
                status=r.status,
                ai_proposal=r.ai_proposal,
                escalation_reason=shown_reason(r.escalation_reason, requested.get(r.id)),
                evidence_strength=r.evidence_strength,
                review_requested=r.id in requested,
                claimed_by_name=claim_user.display_name if live and claim_user else None,
                claimed_by_me=live and r.claimed_by_user_id == user.id,
                final_decision=r.final_decision,
                decided_by_name=decide_user.display_name if decide_user else None,
                decided_at=r.decided_at,
                created_at=r.created_at,
            )
        )
    return out


# --- Case page --------------------------------------------------------------


class CheckOut(BaseModel):
    key: str
    label: str
    state: Literal["pass", "warn", "fail", "info"]
    detail: str
    clauses: list[str] = []


class ClauseOut(BaseModel):
    clause_id: str
    title: str
    body: str
    cited: bool


class PhotoEvidence(BaseModel):
    id: str
    url: str
    width: int | None
    height: int | None
    has_exif: bool | None
    camera: str | None
    captured_at: str | None
    software: str | None
    has_generator_hints: bool | None
    size_bytes: int


class HistoryOut(BaseModel):
    account_age_days: int
    past_orders: int
    past_returns: int
    recent_returns_30d: int
    other_accounts_at_address: int
    risk_score: float | None
    risk_factors: dict[str, float]
    risk_notes: list[str]


class AiOut(BaseModel):
    """What the pipeline concluded. `source` is "rules" until the model steps exist."""

    proposal: Decision | None
    rationale: str | None
    uncertain_about: list[str]
    ambiguous: bool
    critic_concern: str | None
    gate_reasons: list[EscalationReason]
    source: str | None
    ran_at: datetime | None


class ReviewRequestOut(BaseModel):
    customer_explanation: str
    original_decider_name: str
    original_decider_is_me: bool
    status: ReviewRequestStatus
    created_at: datetime


class TimelineEntry(BaseModel):
    at: datetime
    actor_type: str
    actor_name: str | None
    action: str
    details: dict[str, Any]


class CaseOut(BaseModel):
    id: str
    case_number: int
    status: ReturnStatus
    order_number: int
    product_name: str
    product_description: str
    product_category: ProductCategory
    product_photo_url: str | None
    is_final_sale: bool
    reason: ReturnReason
    reason_text: str
    refund_amount_cents: int
    delivered_at: datetime | None
    days_since_delivery: int | None
    created_at: datetime

    escalation_reason: EscalationReason | None
    evidence_strength: EvidenceStrength | None
    checks: list[CheckOut]
    ai: AiOut
    policy_version: int | None
    clauses: list[ClauseOut]
    photos: list[PhotoEvidence]
    history: HistoryOut
    review_request: ReviewRequestOut | None

    claimed_by_name: str | None
    claimed_by_me: bool
    can_decide: bool
    cannot_decide_reason: str | None
    # Re-running the AI checks on a case already with a person (never decides it).
    rerun_pending: bool
    can_rerun: bool
    cannot_rerun_reason: str | None

    final_decision: Decision | None
    decided_by_type: DeciderType | None
    decided_by_name: str | None
    decided_at: datetime | None
    customer_message: str | None

    timeline: list[TimelineEntry]


async def _latest_run(
    db: DbSession, return_id: uuid.UUID
) -> tuple[dict[str, Any], datetime | None]:
    """The outputs of the most recent pipeline run, keyed by step."""
    latest = await db.scalar(
        select(AgentRun)
        .where(AgentRun.return_id == return_id)
        .order_by(AgentRun.created_at.desc())
        .limit(1)
    )
    if latest is None:
        return {}, None
    runs = await db.scalars(
        select(AgentRun).where(AgentRun.run_id == latest.run_id).order_by(AgentRun.created_at)
    )
    return {r.step: (r.output or {}) for r in runs}, latest.created_at


def _checks(
    ret: Return,
    product: Product,
    days: int | None,
    steps: dict[str, Any],
    settings: Settings,
) -> list[CheckOut]:
    """Plain-language rows for the case page, from the stored step outputs."""
    out: list[CheckOut] = []
    dc = steps.get("data_check")
    if dc is not None:
        out.append(
            CheckOut(
                key="data",
                label="Data complete",
                state="pass" if dc.get("complete") else "fail",
                detail="Everything needed was provided."
                if dc.get("complete")
                else "Missing: " + ", ".join(dc.get("missing", [])),
                clauses=["P4"] if "photo" in dc.get("missing", []) else [],
            )
        )
    if days is not None:
        inside = 0 <= days <= RETURN_WINDOW_DAYS
        out.append(
            CheckOut(
                key="window",
                label="Return window",
                state="pass" if inside else "fail",
                detail=f"Requested on day {days} of {RETURN_WINDOW_DAYS}."
                if inside
                else f"Requested on day {days}, after the {RETURN_WINDOW_DAYS}-day window.",
                clauses=["P1"],
            )
        )
    if product.is_final_sale:
        allowed = ret.reason in (
            ReturnReason.DAMAGED,
            ReturnReason.DEFECTIVE,
            ReturnReason.WRONG_ITEM,
        )
        out.append(
            CheckOut(
                key="final_sale",
                label="Final Sale",
                state="warn" if allowed else "fail",
                detail="Final Sale item; returnable only because of the reason given."
                if allowed
                else "Final Sale item, and the reason isn't damage, defect, or wrong item.",
                clauses=["P6"],
            )
        )
    policy = steps.get("policy")
    if policy:
        eligibility = policy.get("eligibility")
        out.append(
            CheckOut(
                key="policy",
                label="Policy eligibility",
                state={"eligible": "pass", "ineligible": "fail"}.get(eligibility, "warn"),
                detail=policy.get("reason") or str(eligibility),
                clauses=list(policy.get("cited_clauses", [])),
            )
        )
    image = steps.get("image")
    if image:
        check = image.get("check")
        notes = " ".join(image.get("notes", []))
        if check == "not_needed":
            out.append(
                CheckOut(key="photo", label="Photo", state="info", detail=notes or "Not needed.")
            )
        else:
            out.append(
                CheckOut(
                    key="photo",
                    label="Photo match and authenticity",
                    state="pass" if check == "verified" else "warn",
                    detail=notes
                    or (
                        "Verified." if check == "verified" else "Not verified — check it yourself."
                    ),
                    clauses=["P4"],
                )
            )
    behavior = steps.get("behavior")
    if behavior and "score" in behavior:
        score = float(behavior["score"])
        limit = float(settings.risk_limit)
        out.append(
            CheckOut(
                key="risk",
                label="Account behaviour",
                state="pass" if score < limit else "warn",
                detail=f"Risk score {score:.2f} (limit {limit:.2f}).",
            )
        )
    high_value = ret.refund_amount_cents > settings.high_value_limit_cents
    limit_text = f"${settings.high_value_limit_cents / 100:,.0f}"
    out.append(
        CheckOut(
            key="value",
            label="Refund value",
            state="warn" if high_value else "pass",
            detail=f"Above the {limit_text} limit: a person must approve."
            if high_value
            else f"Within the {limit_text} limit.",
            clauses=["P7"] if high_value else [],
        )
    )
    critic = steps.get("critic")
    if critic and critic.get("veto"):
        out.append(
            CheckOut(
                key="critic",
                label="Independent re-check",
                state="warn",
                detail=critic.get("concern") or "The critic step raised a concern.",
            )
        )
    return out


def _can_decide(
    ret: Return, user: User, rr: ReviewRequest | None, now: datetime
) -> tuple[bool, str | None]:
    if ret.status not in OPEN_STATUSES:
        return False, "This case has already been decided."
    if (
        rr is not None
        and rr.status is ReviewRequestStatus.OPEN
        and rr.original_decider_id == user.id
    ):
        return (
            False,
            "You made the original denial, so a different reviewer must decide this review.",
        )
    if _claim_is_live(ret, now) and ret.claimed_by_user_id != user.id:
        return False, "Another reviewer is working on this case."
    return True, None


def _model_configured() -> bool:
    return model_client(get_settings()) is not None


async def _rerun_pending(db: DbSession, return_id: uuid.UUID) -> bool:
    job_id = await db.scalar(
        select(Job.id)
        .where(
            Job.return_id == return_id,
            Job.kind == jobs.RERUN_JOB,
            Job.status.in_((JobStatus.QUEUED, JobStatus.RUNNING)),
        )
        .limit(1)
    )
    return job_id is not None


def _can_rerun(ret: Return, user: User, pending: bool, now: datetime) -> tuple[bool, str | None]:
    if ret.status not in OPEN_STATUSES:
        return False, "This case has already been decided."
    if pending:
        return False, "The AI checks are already re-running."
    if _claim_is_live(ret, now) and ret.claimed_by_user_id != user.id:
        return False, "Another reviewer is working on this case."
    if not _model_configured():
        return False, "No AI model is configured, so a re-run would only repeat the rules."
    return True, None


async def _load_case(db: DbSession, return_id: uuid.UUID, *, lock: bool = False) -> Return:
    stmt = select(Return).where(Return.id == return_id).execution_options(populate_existing=True)
    if lock:
        stmt = stmt.with_for_update()
    ret = await db.scalar(stmt)
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found")
    return ret


async def _case_out(db: DbSession, ret: Return, user: User) -> CaseOut:
    now = datetime.now(UTC)
    item = await db.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(
            selectinload(OrderItem.product).options(WITH_PHOTOS), selectinload(OrderItem.order)
        )
    )
    assert item is not None
    order, product = item.order, item.product
    customer = await db.get_one(User, ret.customer_id)
    settings = await db.get_one(Settings, 1)
    photos = list(
        await db.scalars(
            select(ReturnPhoto)
            .where(ReturnPhoto.return_id == ret.id)
            .order_by(ReturnPhoto.created_at)
        )
    )
    steps, ran_at = await _latest_run(db, ret.id)
    days = days_since_delivery(order.delivered_at, ret.created_at) if order.delivered_at else None

    policy_doc = await db.scalar(
        select(PolicyDoc)
        .where(
            PolicyDoc.version == ret.policy_version
            if ret.policy_version is not None
            else PolicyDoc.is_active
        )
        .options(selectinload(PolicyDoc.chunks))
    )
    checks = _checks(ret, product, days, steps, settings)
    cited = {c for check in checks for c in check.clauses}
    clauses = (
        sorted(
            (
                ClauseOut(
                    clause_id=c.clause_id, title=c.title, body=c.body, cited=c.clause_id in cited
                )
                for c in policy_doc.chunks
            ),
            key=lambda c: int(c.clause_id[1:]) if c.clause_id[1:].isdigit() else 99,
        )
        if policy_doc
        else []
    )

    hist = await behavior_inputs(db, ret, order, customer, settings.high_value_limit_cents)
    behavior = steps.get("behavior") or {}
    rec = steps.get("recommendation") or {}
    critic = steps.get("critic") or {}
    gate = steps.get("gate") or {}

    rr = await db.scalar(select(ReviewRequest).where(ReviewRequest.return_id == ret.id))
    rr_out = None
    if rr is not None:
        original = await db.get_one(User, rr.original_decider_id)
        rr_out = ReviewRequestOut(
            customer_explanation=rr.customer_explanation,
            original_decider_name=original.display_name,
            original_decider_is_me=original.id == user.id,
            status=rr.status,
            created_at=rr.created_at,
        )

    claimer = (
        await db.get(User, ret.claimed_by_user_id)
        if ret.claimed_by_user_id and _claim_is_live(ret, now)
        else None
    )
    decider = await db.get(User, ret.decided_by_user_id) if ret.decided_by_user_id else None
    can, why_not = _can_decide(ret, user, rr, now)
    rerun_pending = await _rerun_pending(db, ret.id)
    can_rerun, why_not_rerun = _can_rerun(ret, user, rerun_pending, now)

    entries = list(
        await db.scalars(select(AuditLog).where(AuditLog.return_id == ret.id).order_by(AuditLog.id))
    )
    actor_ids = {e.actor_user_id for e in entries if e.actor_user_id}
    staff_names = {
        u.id: u.display_name
        for u in await db.scalars(
            select(User).where(User.id.in_(actor_ids), User.role != Role.CUSTOMER)
        )
    }

    return CaseOut(
        id=str(ret.id),
        case_number=ret.case_number,
        status=ret.status,
        order_number=order.order_number,
        product_name=product.name,
        product_description=product.description,
        product_category=product.category,
        product_photo_url=main_photo_url(product),
        is_final_sale=product.is_final_sale,
        reason=ret.reason,
        reason_text=ret.reason_text,
        refund_amount_cents=ret.refund_amount_cents,
        delivered_at=order.delivered_at,
        days_since_delivery=days,
        created_at=ret.created_at,
        escalation_reason=shown_reason(ret.escalation_reason, rr.status if rr else None),
        evidence_strength=ret.evidence_strength,
        checks=checks,
        ai=AiOut(
            proposal=ret.ai_proposal,
            rationale=rec.get("rationale"),
            uncertain_about=list(rec.get("uncertain_about", [])),
            ambiguous=bool(rec.get("ambiguous", False)),
            critic_concern=critic.get("concern"),
            gate_reasons=[EscalationReason(r) for r in gate.get("reasons", [])],
            source=rec.get("source"),
            ran_at=ran_at,
        ),
        policy_version=policy_doc.version if policy_doc else None,
        clauses=clauses,
        photos=[
            PhotoEvidence(
                id=str(p.id),
                url=f"/api/returns/{ret.id}/photos/{p.id}",
                width=p.metadata_summary.get("width"),
                height=p.metadata_summary.get("height"),
                has_exif=p.metadata_summary.get("has_exif"),
                camera=" ".join(
                    v
                    for v in (
                        p.metadata_summary.get("camera_make"),
                        p.metadata_summary.get("camera_model"),
                    )
                    if v
                )
                or None,
                captured_at=p.metadata_summary.get("captured_at"),
                software=p.metadata_summary.get("software"),
                has_generator_hints=p.metadata_summary.get("has_generator_hints"),
                size_bytes=p.size_bytes,
            )
            for p in photos
        ],
        history=HistoryOut(
            account_age_days=hist.account_age_days,
            past_orders=hist.past_orders,
            past_returns=hist.past_returns,
            recent_returns_30d=hist.recent_returns_30d,
            other_accounts_at_address=hist.other_accounts_at_address,
            risk_score=behavior.get("score"),
            risk_factors={k: float(v) for k, v in (behavior.get("factors") or {}).items()},
            risk_notes=list(behavior.get("explanation", [])),
        ),
        review_request=rr_out,
        claimed_by_name=claimer.display_name if claimer else None,
        claimed_by_me=claimer is not None and claimer.id == user.id,
        can_decide=can,
        cannot_decide_reason=why_not,
        rerun_pending=rerun_pending,
        can_rerun=can_rerun,
        cannot_rerun_reason=why_not_rerun,
        final_decision=ret.final_decision,
        decided_by_type=ret.decided_by_type,
        decided_by_name=decider.display_name if decider else None,
        decided_at=ret.decided_at,
        customer_message=ret.customer_message,
        timeline=[
            TimelineEntry(
                at=e.created_at,
                actor_type=e.actor_type.value,
                actor_name=staff_names.get(e.actor_user_id) if e.actor_user_id else None,
                action=e.action,
                details=e.details,
            )
            for e in entries
        ],
    )


@router.get("/cases/{return_id}", response_model=CaseOut)
async def get_case(return_id: uuid.UUID, user: Reviewer, db: DbSession) -> CaseOut:
    return await _case_out(db, await _load_case(db, return_id), user)


@router.post("/cases/{return_id}/rerun", response_model=CaseOut)
async def rerun_case(
    return_id: uuid.UUID, user: Reviewer, db: DbSession, background: BackgroundTasks
) -> CaseOut:
    """Re-run the AI checks on a case already with a person, e.g. one first checked
    before a model was configured, or after a pipeline error. The fresh run replaces
    what the case page shows; the case stays with the reviewer and is never decided
    by it (pipeline.runner.review_return, rerun=True)."""
    ret = await _load_case(db, return_id, lock=True)
    can, why_not = _can_rerun(ret, user, await _rerun_pending(db, ret.id), datetime.now(UTC))
    if not can:
        raise HTTPException(status.HTTP_409_CONFLICT, why_not)
    # Outbox, as with a new return: the job is committed with the audit entry.
    db.add(Job(kind=jobs.RERUN_JOB, return_id=ret.id))
    audit.record(
        db,
        actor_type=audit.actor_for_role(user.role),
        actor_user_id=user.id,
        action="review.rerun_requested",
        return_id=ret.id,
    )
    await db.commit()
    background.add_task(nudge_worker)
    log.info("review.rerun_requested", case_number=ret.case_number)
    return await _case_out(db, await _load_case(db, return_id), user)


# --- Claims -----------------------------------------------------------------


@router.post("/cases/{return_id}/claim", response_model=CaseOut)
async def claim_case(return_id: uuid.UUID, user: Reviewer, db: DbSession) -> CaseOut:
    """Take the case, so other reviewers see someone is on it."""
    ret = await _load_case(db, return_id, lock=True)
    now = datetime.now(UTC)
    if ret.status not in OPEN_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "This case has already been decided.")
    if _claim_is_live(ret, now) and ret.claimed_by_user_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Another reviewer is working on this case.")
    first_claim = ret.claimed_by_user_id != user.id or not _claim_is_live(ret, now)
    ret.claimed_by_user_id = user.id
    ret.claimed_at = now
    if first_claim:
        audit.record(
            db,
            actor_type=audit.actor_for_role(user.role),
            actor_user_id=user.id,
            action="review.claimed",
            return_id=ret.id,
        )
    await db.commit()
    return await _case_out(db, await _load_case(db, return_id), user)


@router.delete("/cases/{return_id}/claim", response_model=CaseOut)
async def release_case(return_id: uuid.UUID, user: Reviewer, db: DbSession) -> CaseOut:
    """Hand the case back to the queue."""
    ret = await _load_case(db, return_id, lock=True)
    if ret.claimed_by_user_id == user.id:
        ret.claimed_by_user_id = None
        ret.claimed_at = None
        audit.record(
            db,
            actor_type=audit.actor_for_role(user.role),
            actor_user_id=user.id,
            action="review.released",
            return_id=ret.id,
        )
        await db.commit()
    return await _case_out(db, await _load_case(db, return_id), user)


# --- Decision ---------------------------------------------------------------


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "deny"]
    # The clause(s) the decision rests on. Required for a denial (M7).
    policy_clauses: list[str] = Field(default_factory=list, max_length=9)
    # Required when the decision differs from the AI's approve/deny proposal.
    override_reason: OverrideReason | None = None
    override_note: str = Field(default="", max_length=200)
    # Optional words for the customer, added to their message.
    note_to_customer: str = Field(default="", max_length=MAX_NOTE_LENGTH)
    # A denial is never one accidental click (M1).
    confirm_denial: bool = False


def _customer_message(
    *,
    decision: Decision,
    ret: Return,
    order: Order,
    clauses: list[tuple[str, str]],
    note: str,
    re_review: bool,
) -> str:
    refund = f"${ret.refund_amount_cents / 100:,.2f}"
    parts: list[str] = []
    if decision is Decision.APPROVE:
        who = (
            "After looking at it again, a different member of our team approved your return."
            if re_review
            else "Your return was approved by a member of our team."
        )
        parts.append(
            f"{who} A refund of {refund} will be issued to your original payment method "
            "within 5 to 7 business days (P9)."
        )
    else:
        rule = "; ".join(f"{cid} — {title}" for cid, title in clauses)
        parts.append(f"Your return was not approved. Policy rule: {rule}.")
        considered = [f'reason "{REASON_LABELS[ret.reason]}"']
        if order.delivered_at is not None:
            day = days_since_delivery(order.delivered_at, ret.created_at)
            considered.insert(
                0, f"delivered {shop_date(order.delivered_at):%d %b %Y} (requested on day {day})"
            )
        parts.append("We considered: " + " · ".join(considered) + ".")
    if note.strip():
        parts.append(note.strip())
    if decision is Decision.DENY:
        if re_review:
            parts.append(
                "Your review request was looked at by a different member of our team "
                "from the one who made the first decision. This is our final decision."
            )
        else:
            parts.append(
                "This decision was made by a member of our team, not automatically. "
                "If you think we got it wrong, you can request a review."
            )
    return " ".join(parts)


@router.post("/cases/{return_id}/decision", response_model=CaseOut)
async def decide_case(
    return_id: uuid.UUID, body: DecisionIn, user: Reviewer, db: DbSession
) -> CaseOut:
    ret = await _load_case(db, return_id, lock=True)
    now = datetime.now(UTC)
    rr = await db.scalar(
        select(ReviewRequest).where(ReviewRequest.return_id == ret.id).with_for_update()
    )
    can, why_not = _can_decide(ret, user, rr, now)
    if not can:
        raise HTTPException(status.HTTP_409_CONFLICT, why_not)

    decision = Decision(body.decision)
    item = await db.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(selectinload(OrderItem.product), selectinload(OrderItem.order))
    )
    assert item is not None

    # The clauses must exist in the policy version this case was checked against.
    policy_doc = await db.scalar(
        select(PolicyDoc)
        .where(
            PolicyDoc.version == ret.policy_version
            if ret.policy_version is not None
            else PolicyDoc.is_active
        )
        .options(selectinload(PolicyDoc.chunks))
    )
    known = {c.clause_id: c.title for c in (policy_doc.chunks if policy_doc else [])}
    chosen = list(dict.fromkeys(body.policy_clauses))
    if unknown := [c for c in chosen if c not in known]:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown policy clause: {', '.join(unknown)}"
        )

    if decision is Decision.DENY:
        if not body.confirm_denial:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Please confirm the denial.")
        if not chosen:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Choose the policy rule the denial is based on.",
            )

    disagrees = ret.ai_proposal in (Decision.APPROVE, Decision.DENY) and decision != ret.ai_proposal
    if disagrees and body.override_reason is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "You're disagreeing with the AI: choose a reason.",
        )
    if body.override_reason is OverrideReason.OTHER and not body.override_note.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Say briefly why you disagree.")
    override = None
    if body.override_reason is not None:
        override = body.override_reason.value
        if body.override_note.strip():
            override = f"{override}: {body.override_note.strip()}"[:100]

    re_review = rr is not None and rr.status is ReviewRequestStatus.OPEN
    previous_reason = ret.escalation_reason
    ret.status = ReturnStatus.APPROVED if decision is Decision.APPROVE else ReturnStatus.DENIED
    ret.final_decision = decision
    ret.decided_by_type = DeciderType.PERSON
    ret.decided_by_user_id = user.id
    ret.decided_at = now
    ret.route = Route.REVIEWER
    ret.claimed_by_user_id = None
    ret.claimed_at = None
    ret.customer_message = _customer_message(
        decision=decision,
        ret=ret,
        order=item.order,
        clauses=[(c, known[c]) for c in chosen],
        note=body.note_to_customer,
        re_review=re_review,
    )
    if rr is not None and re_review:
        rr.assigned_reviewer_id = user.id
        rr.status = ReviewRequestStatus.RESOLVED
        rr.outcome = decision
        rr.resolved_at = now

    # One sample per return: the first person's call against the AI's. A re-review is
    # recorded on the review request (outcome), not as a second sample.
    if ret.ai_proposal in (Decision.APPROVE, Decision.DENY) and not re_review:
        db.add(
            AgreementSample(
                return_id=ret.id,
                reviewer_id=user.id,
                kind=AgreementKind.QA_SAMPLE
                if previous_reason is EscalationReason.QA_SAMPLE
                else (AgreementKind.OVERRIDE if disagrees else AgreementKind.AGREEMENT),
                ai_proposal=ret.ai_proposal,
                human_decision=decision,
                agreed=not disagrees,
                override_reason=override,
                product_category=item.product.category,
                escalation_reason=previous_reason,
            )
        )
    audit.record(
        db,
        actor_type=audit.actor_for_role(user.role),
        actor_user_id=user.id,
        action="review.approved" if decision is Decision.APPROVE else "review.denied",
        return_id=ret.id,
        details={
            "decision": decision.value,
            "ai_proposal": ret.ai_proposal.value if ret.ai_proposal else None,
            "agreed_with_ai": None
            if ret.ai_proposal not in (Decision.APPROVE, Decision.DENY)
            else not disagrees,
            "override_reason": override,
            "policy_clauses": chosen,
            "escalation_reason": previous_reason.value if previous_reason else None,
            "review_request": re_review,
        },
    )
    await db.commit()
    log.info(
        "review.decided",
        case_number=ret.case_number,
        decision=decision.value,
        agreed=not disagrees,
        re_review=re_review,
    )
    return await _case_out(db, await _load_case(db, return_id), user)
