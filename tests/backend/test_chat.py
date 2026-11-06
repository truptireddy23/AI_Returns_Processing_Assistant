"""The return chat thread (M9): customer messages, the bot's auto-reply, and a
reviewer taking the thread over."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.config import get_settings
from returnguard.models import AuditLog, MessageSender, ReturnMessage, Role, User
from returnguard.pipeline.chat_assist import FALLBACK_REPLY

from .factories import make_user
from .test_pipeline import make_return
from .test_review import signed_in

pytestmark = pytest.mark.db


# --- Customer: send and list ------------------------------------------------


async def test_customer_can_send_and_list_messages(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    headers = await signed_in(db_client, customer)

    res = await db_client.post(
        f"/api/returns/{ret.id}/messages", json={"body": "Hi, any update?"}, headers=headers
    )

    assert res.status_code == 201, res.text
    messages = res.json()
    assert messages[0]["sender"] == "customer"
    assert messages[0]["body"] == "Hi, any update?"

    listed = await db_client.get(f"/api/returns/{ret.id}/messages", headers=headers)
    assert listed.status_code == 200
    assert [m["body"] for m in listed.json()] == [m["body"] for m in messages]


async def test_the_bot_auto_replies_with_the_fixed_message_when_no_key_is_configured(
    db_client: httpx.AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """With neither GROQ_API_KEY nor OPENAI_API_KEY set, the bot's only honest option
    is the fixed fallback reply — never a guess. Explicitly cleared (not just relying
    on the ambient environment) so this holds even when a developer's app/.env has
    real keys set for manual testing."""
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    request.addfinalizer(get_settings.cache_clear)
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    headers = await signed_in(db_client, customer)

    res = await db_client.post(
        f"/api/returns/{ret.id}/messages", json={"body": "What's happening?"}, headers=headers
    )

    messages = res.json()
    assert len(messages) == 2
    assert messages[1]["sender"] == "bot"
    assert messages[1]["body"] == FALLBACK_REPLY


async def test_an_empty_message_is_rejected(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    headers = await signed_in(db_client, customer)

    res = await db_client.post(
        f"/api/returns/{ret.id}/messages", json={"body": ""}, headers=headers
    )

    assert res.status_code == 422


async def test_a_customer_cannot_see_or_message_another_customers_return(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    other = await make_user(db_session)
    headers = await signed_in(db_client, other)

    listed = await db_client.get(f"/api/returns/{ret.id}/messages", headers=headers)
    assert listed.status_code == 404
    res = await db_client.post(
        f"/api/returns/{ret.id}/messages", json={"body": "hi"}, headers=headers
    )
    assert res.status_code == 404


# --- Reviewer: visibility and taking the thread over ------------------------


async def test_only_staff_can_see_or_send_reviewer_side_messages(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    headers = await signed_in(db_client, customer)

    assert (
        await db_client.get(f"/api/review/cases/{ret.id}/messages", headers=headers)
    ).status_code == 403
    res = await db_client.post(
        f"/api/review/cases/{ret.id}/messages", json={"body": "hi"}, headers=headers
    )
    assert res.status_code == 403


async def test_a_reviewer_message_is_recorded_and_audited(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    res = await db_client.post(
        f"/api/review/cases/{ret.id}/messages",
        json={"body": "Could you send another photo?"},
        headers=headers,
    )

    assert res.status_code == 201, res.text
    messages = res.json()
    assert messages[-1] == {
        "id": messages[-1]["id"],
        "sender": "reviewer",
        "body": "Could you send another photo?",
        "created_at": messages[-1]["created_at"],
    }
    entries = list(
        await db_session.scalars(
            select(AuditLog).where(
                AuditLog.return_id == ret.id, AuditLog.action == "return.message_sent"
            )
        )
    )
    assert len(entries) == 1
    assert entries[0].actor_user_id == reviewer.id


async def test_the_bot_stops_answering_once_a_reviewer_has_replied(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    reviewer = await make_user(db_session, Role.REVIEWER)

    reviewer_headers = await signed_in(db_client, reviewer)
    await db_client.post(
        f"/api/review/cases/{ret.id}/messages",
        json={"body": "I'm looking into this for you."},
        headers=reviewer_headers,
    )

    customer_headers = await signed_in(db_client, customer)
    res = await db_client.post(
        f"/api/returns/{ret.id}/messages",
        json={"body": "Thank you, when will I hear back?"},
        headers=customer_headers,
    )

    messages = res.json()
    # The reviewer's message, the customer's — and no bot message after it.
    assert [m["sender"] for m in messages] == ["reviewer", "customer"]
    senders = list(
        await db_session.scalars(
            select(ReturnMessage.sender).where(ReturnMessage.return_id == ret.id)
        )
    )
    assert MessageSender.BOT not in senders
