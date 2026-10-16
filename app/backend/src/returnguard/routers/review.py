"""Reviewer: the queue of cases that need a person (screens arrive in M7)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from returnguard.auth import DbSession, require_role
from returnguard.models import Decision, EscalationReason, Return, ReturnStatus, Role, User

router = APIRouter(prefix="/api/review", tags=["review"])

# Admins hold every reviewer right (DESIGN_SPEC.md decision-rights table).
Reviewer = Annotated[User, Depends(require_role(Role.REVIEWER, Role.ADMIN))]


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
