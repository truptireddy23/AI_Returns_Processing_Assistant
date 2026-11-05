"""Admin: automation settings, the oversight dashboard, and the audit log (M8, S1, C1).

Settings take effect immediately: the pipeline reads the single `settings` row for
every return it checks, and the reviewer's case page compares against the current
values. Cases already in the queue keep the reason they were escalated for; the
audit log records every change, with the old and new values.

The admin can't change the fixed rules (the AI never denies; unverified photos are
never auto-approved; ambiguous calls always go to a person): they're code in
`pipeline/gate.py`, not settings.
"""

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard import audit
from returnguard.auth import DbSession, require_role
from returnguard.models import (
    ActorType,
    AgreementSample,
    AuditLog,
    DeciderType,
    Decision,
    PolicyDoc,
    Return,
    ReviewRequest,
    Role,
    Route,
    Settings,
    User,
)
from returnguard.routers.review import OPEN_STATUSES, shown_reason

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

Admin = Annotated[User, Depends(require_role(Role.ADMIN))]

AGREEMENT_SAMPLE_SIZE = 50  # "Reviewer agreed with AI: x% of the last 50 decisions"


# --- Settings ---------------------------------------------------------------


class SettingsOut(BaseModel):
    automation_enabled: bool
    risk_limit: Decimal
    high_value_limit_cents: int
    qa_sample_rate: Decimal
    updated_at: datetime
    updated_by_name: str | None
    # The amount in the written policy's high-value clause (P7), so the UI can warn
    # when the setting would auto-approve refunds the policy says need a manager.
    policy_high_value_cents: int | None


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automation_enabled: bool
    risk_limit: Decimal = Field(ge=0, le=1, decimal_places=2)
    high_value_limit_cents: int = Field(ge=100, le=10_000_00)  # $1 to $10,000
    qa_sample_rate: Decimal = Field(ge=0, le=1, decimal_places=2)


async def _policy_high_value_cents(db: DbSession) -> int | None:
    doc = await db.scalar(
        select(PolicyDoc).where(PolicyDoc.is_active).options(selectinload(PolicyDoc.chunks))
    )
    p7 = next((c for c in doc.chunks if c.clause_id == "P7"), None) if doc else None
    match = re.search(r"\$\s?([\d,]+(?:\.\d{2})?)", p7.body) if p7 else None
    if not match:
        return None
    return round(float(match.group(1).replace(",", "")) * 100)


async def _settings_out(db: DbSession, row: Settings) -> SettingsOut:
    editor = await db.get(User, row.updated_by_user_id) if row.updated_by_user_id else None
    return SettingsOut(
        automation_enabled=row.automation_enabled,
        risk_limit=row.risk_limit,
        high_value_limit_cents=row.high_value_limit_cents,
        qa_sample_rate=row.qa_sample_rate,
        updated_at=row.updated_at,
        updated_by_name=editor.display_name if editor else None,
        policy_high_value_cents=await _policy_high_value_cents(db),
    )


@router.get("/settings", response_model=SettingsOut)
async def get_settings(_: Admin, db: DbSession) -> SettingsOut:
    row = await db.get_one(Settings, 1, populate_existing=True)
    return await _settings_out(db, row)


@router.put("/settings", response_model=SettingsOut)
async def update_settings(body: SettingsIn, user: Admin, db: DbSession) -> SettingsOut:
    row = await db.get_one(Settings, 1, with_for_update=True, populate_existing=True)
    new: dict[str, Any] = body.model_dump()
    changes = {
        field: [_plain(getattr(row, field)), _plain(value)]
        for field, value in new.items()
        if getattr(row, field) != value
    }
    if changes:
        for field, value in new.items():
            setattr(row, field, value)
        row.updated_by_user_id = user.id
        row.updated_at = datetime.now(UTC)
        audit.record(
            db,
            actor_type=ActorType.ADMIN,
            actor_user_id=user.id,
            action="admin.settings_changed",
            details={"changes": changes},
        )
        await db.commit()
        log.info("admin.settings_changed", fields=sorted(changes))
    row = await db.get_one(Settings, 1, populate_existing=True)
    return await _settings_out(db, row)


def _plain(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else value


# --- Dashboard --------------------------------------------------------------


class Rate(BaseModel):
    key: str
    total: int
    agreed: int


class CountByKey(BaseModel):
    key: str
    count: int


class ReviewerLoad(BaseModel):
    name: str
    approved: int
    denied: int


class MetricsOut(BaseModel):
    days: int
    since: datetime
    returns_started: int
    auto_approved: int
    sent_to_person: int
    waiting_on_customer: int
    escalation_rate: float | None  # sent to a person / (auto-approved + sent to a person)
    open_now: int
    oldest_open_at: datetime | None
    open_by_reason: list[CountByKey]
    escalations_by_reason: list[CountByKey]
    approved_by_people: int
    denied_by_people: int
    avg_hours_to_decision: float | None
    reviewers: list[ReviewerLoad]
    agreement_sample_size: int
    agreement_total: int
    agreement_agreed: int
    agreement_by_category: list[Rate]
    agreement_by_reason: list[Rate]
    top_overrides: list[CountByKey]


@router.get("/metrics", response_model=MetricsOut)
async def metrics(
    _: Admin,
    db: DbSession,
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> MetricsOut:
    """Where is the AI working, where isn't it, and is the gate flooding reviewers?"""
    since = datetime.now(UTC) - timedelta(days=days)

    # Routing of returns started in the window.
    recent = list(
        await db.execute(
            select(Return.route, Return.decided_by_type, Return.escalation_reason).where(
                Return.created_at >= since
            )
        )
    )
    auto = sum(1 for route, decider, _ in recent if decider is DeciderType.AUTO)
    to_person = sum(1 for route, _, _ in recent if route is Route.REVIEWER)
    to_customer = sum(1 for route, _, _ in recent if route is Route.CUSTOMER)
    by_reason = Counter(
        reason.value for route, _, reason in recent if route is Route.REVIEWER and reason
    )

    open_rows = list(
        await db.execute(
            select(Return.escalation_reason, Return.created_at, ReviewRequest.status)
            .outerjoin(ReviewRequest, ReviewRequest.return_id == Return.id)
            .where(Return.status.in_(OPEN_STATUSES))
        )
    )
    open_reason = Counter(
        (reason.value if (reason := shown_reason(r, rr_status)) else "none")
        for r, _, rr_status in open_rows
    )

    # Decisions by people in the window.
    decided = list(
        await db.execute(
            select(Return.final_decision, Return.created_at, Return.decided_at, User.display_name)
            .join(User, User.id == Return.decided_by_user_id)
            .where(Return.decided_by_type == DeciderType.PERSON, Return.decided_at >= since)
        )
    )
    loads: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    hours = []
    for decision, created, decided_at, name in decided:
        loads[name][0 if decision is Decision.APPROVE else 1] += 1
        if decided_at and created:
            hours.append((decided_at - created).total_seconds() / 3600)

    # Agreement: the last N reviewer decisions on cases where the AI proposed one.
    samples = list(
        await db.scalars(
            select(AgreementSample)
            .order_by(AgreementSample.created_at.desc())
            .limit(AGREEMENT_SAMPLE_SIZE)
        )
    )

    def rates(keyed: list[tuple[str, bool]]) -> list[Rate]:
        totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for key, agreed in keyed:
            totals[key][0] += 1
            totals[key][1] += int(agreed)
        return sorted(
            (Rate(key=k, total=t, agreed=a) for k, (t, a) in totals.items()),
            key=lambda r: (-r.total, r.key),
        )

    overrides = Counter((s.override_reason or "").split(":", 1)[0] for s in samples if not s.agreed)

    return MetricsOut(
        days=days,
        since=since,
        returns_started=len(recent),
        auto_approved=auto,
        sent_to_person=to_person,
        waiting_on_customer=to_customer,
        escalation_rate=to_person / (auto + to_person) if auto + to_person else None,
        open_now=len(open_rows),
        oldest_open_at=min((c for _, c, _ in open_rows), default=None),
        open_by_reason=[CountByKey(key=k, count=v) for k, v in open_reason.most_common()],
        escalations_by_reason=[CountByKey(key=k, count=v) for k, v in by_reason.most_common()],
        approved_by_people=sum(1 for d, *_ in decided if d is Decision.APPROVE),
        denied_by_people=sum(1 for d, *_ in decided if d is Decision.DENY),
        avg_hours_to_decision=round(sum(hours) / len(hours), 1) if hours else None,
        reviewers=sorted(
            (ReviewerLoad(name=n, approved=a, denied=d) for n, (a, d) in loads.items()),
            key=lambda r: -(r.approved + r.denied),
        ),
        agreement_sample_size=AGREEMENT_SAMPLE_SIZE,
        agreement_total=len(samples),
        agreement_agreed=sum(1 for s in samples if s.agreed),
        agreement_by_category=rates([(s.product_category.value, s.agreed) for s in samples]),
        agreement_by_reason=rates(
            [
                (s.escalation_reason.value if s.escalation_reason else "none", s.agreed)
                for s in samples
            ]
        ),
        top_overrides=[CountByKey(key=k or "other", count=v) for k, v in overrides.most_common(5)],
    )


# --- Audit log ----------------------------------------------------------------


class AuditEntryOut(BaseModel):
    id: int
    at: datetime
    actor_type: ActorType
    actor_name: str | None
    action: str
    return_id: str | None
    case_number: int | None
    details: dict[str, Any]


class AuditPage(BaseModel):
    entries: list[AuditEntryOut]
    next_before_id: int | None  # pass as `before_id` for the next (older) page


@router.get("/audit", response_model=AuditPage)
async def audit_log(
    _: Admin,
    db: DbSession,
    actor_type: Annotated[ActorType | None, Query()] = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
    case_number: Annotated[int | None, Query(ge=1)] = None,
    before_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditPage:
    """Every check, gate decision, and human action, newest first (C1).

    `action` matches a prefix, e.g. `review.` for all reviewer actions."""
    stmt = (
        select(AuditLog, Return.case_number)
        .outerjoin(Return, Return.id == AuditLog.return_id)
        .order_by(AuditLog.id.desc())
        .limit(limit + 1)
    )
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action.startswith(action, autoescape=True))
    if case_number is not None:
        stmt = stmt.where(Return.case_number == case_number)
    if before_id is not None:
        stmt = stmt.where(AuditLog.id < before_id)
    rows = list(await db.execute(stmt))
    more = len(rows) > limit
    rows = rows[:limit]

    # Staff are named; customers are shown by role only (privacy).
    ids = {e.actor_user_id for e, _ in rows if e.actor_user_id}
    names = {
        u.id: u.display_name
        for u in await db.scalars(select(User).where(User.id.in_(ids), User.role != Role.CUSTOMER))
    }
    return AuditPage(
        entries=[
            AuditEntryOut(
                id=e.id,
                at=e.created_at,
                actor_type=e.actor_type,
                actor_name=names.get(e.actor_user_id) if e.actor_user_id else None,
                action=e.action,
                return_id=str(e.return_id) if e.return_id else None,
                case_number=case,
                details=e.details,
            )
            for e, case in rows
        ],
        next_before_id=rows[-1][0].id if more and rows else None,
    )
