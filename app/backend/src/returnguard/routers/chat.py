"""A return's chat thread (M9): the customer's questions, answered by the AI
assistant until a reviewer takes the thread over.

The bot never decides anything — it only drafts a reply, grounded in the case's own
facts and the retrieved policy clauses, and it stops answering the moment any
reviewer has sent a message in that thread (`chat_assist.thread_taken_over`), so a
human and the bot are never talking to the same customer about the same case at once.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import audit
from returnguard.auth import DbSession, require_role
from returnguard.config import get_settings
from returnguard.models import (
    ActorType,
    MessageSender,
    Order,
    OrderItem,
    PolicyDoc,
    Return,
    ReturnMessage,
    Role,
    User,
)
from returnguard.pipeline.chat_assist import (
    ChatCase,
    default_clients,
    draft_reply,
    thread_taken_over,
)
from returnguard.pipeline.privacy import identity_terms
from returnguard.ratelimit import rate_limit

router = APIRouter(prefix="/api", tags=["chat"])

Customer = Annotated[User, Depends(require_role(Role.CUSTOMER))]
# Admins hold every reviewer right, same as the rest of the review surface.
Reviewer = Annotated[User, Depends(require_role(Role.REVIEWER, Role.ADMIN))]

MAX_MESSAGE_LENGTH = 2000


class MessageOut(BaseModel):
    id: int
    sender: str
    body: str
    created_at: datetime


class MessageIn(BaseModel):
    body: Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)]


async def _load_for_customer(db: AsyncSession, return_id: uuid.UUID, user: User) -> Return:
    ret = await db.get(Return, return_id)
    if ret is None or ret.customer_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    return ret


async def _load_for_staff(db: AsyncSession, return_id: uuid.UUID) -> Return:
    ret = await db.get(Return, return_id)
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Return not found")
    return ret


async def _list_messages(db: AsyncSession, return_id: uuid.UUID) -> list[MessageOut]:
    rows = await db.scalars(
        select(ReturnMessage)
        .where(ReturnMessage.return_id == return_id)
        .order_by(ReturnMessage.created_at)
    )
    return [
        MessageOut(id=m.id, sender=m.sender.value, body=m.body, created_at=m.created_at)
        for m in rows
    ]


async def _post_message_and_maybe_reply(
    db: AsyncSession, ret: Return, *, sender: MessageSender, user: User, body: str
) -> list[MessageOut]:
    db.add(ReturnMessage(return_id=ret.id, sender=sender, sender_user_id=user.id, body=body))
    audit.record(
        db,
        actor_type=audit.actor_for_role(user.role),
        actor_user_id=user.id,
        action="return.message_sent",
        return_id=ret.id,
    )
    await db.commit()

    if sender is MessageSender.CUSTOMER and not await thread_taken_over(db, ret.id):
        embedder, chat = default_clients()
        policy = await db.scalar(select(PolicyDoc).where(PolicyDoc.is_active))
        order = await db.scalar(
            select(Order).join(OrderItem).where(OrderItem.id == ret.order_item_id)
        )
        assert order is not None
        reply = await draft_reply(
            db,
            embedder=embedder,
            chat=chat,
            policy_doc_id=policy.id if policy else None,
            case=ChatCase(
                status=ret.status,
                reason=ret.reason.value,
                refund_cents=ret.refund_amount_cents,
                escalation_reason=ret.escalation_reason,
                final_decision=ret.final_decision,
            ),
            customer_message=body,
            identifiers=identity_terms(user, order),
        )
        db.add(ReturnMessage(return_id=ret.id, sender=MessageSender.BOT, body=reply.body))
        audit.record(
            db,
            actor_type=ActorType.AI,
            action="return.chat_bot_replied",
            return_id=ret.id,
            details={"escalate": reply.escalate, "source": reply.source},
        )
        await db.commit()

    return await _list_messages(db, ret.id)


# --- Customer -----------------------------------------------------------------


@router.get("/returns/{return_id}/messages", response_model=list[MessageOut])
async def list_customer_messages(
    return_id: uuid.UUID, user: Customer, db: DbSession
) -> list[MessageOut]:
    ret = await _load_for_customer(db, return_id, user)
    return await _list_messages(db, ret.id)


@router.post(
    "/returns/{return_id}/messages",
    response_model=list[MessageOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(get_settings().chat_rate_limit, "chat"))],
)
async def send_customer_message(
    return_id: uuid.UUID, body: MessageIn, user: Customer, db: DbSession
) -> list[MessageOut]:
    ret = await _load_for_customer(db, return_id, user)
    return await _post_message_and_maybe_reply(
        db, ret, sender=MessageSender.CUSTOMER, user=user, body=body.body.strip()
    )


# --- Reviewer -------------------------------------------------------------------


@router.get("/review/cases/{return_id}/messages", response_model=list[MessageOut])
async def list_reviewer_messages(
    return_id: uuid.UUID, user: Reviewer, db: DbSession
) -> list[MessageOut]:
    ret = await _load_for_staff(db, return_id)
    return await _list_messages(db, ret.id)


@router.post(
    "/review/cases/{return_id}/messages",
    response_model=list[MessageOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(get_settings().chat_rate_limit, "chat"))],
)
async def send_reviewer_message(
    return_id: uuid.UUID, body: MessageIn, user: Reviewer, db: DbSession
) -> list[MessageOut]:
    ret = await _load_for_staff(db, return_id)
    return await _post_message_and_maybe_reply(
        db, ret, sender=MessageSender.REVIEWER, user=user, body=body.body.strip()
    )
