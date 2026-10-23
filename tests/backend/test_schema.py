"""Database-level guarantees that hold no matter what the application code does."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import audit
from returnguard.db import Base
from returnguard.models import (
    ActorType,
    AuditLog,
    DeciderType,
    Decision,
    Return,
    ReturnReason,
    ReturnStatus,
    ReviewRequest,
    Role,
)

from .factories import make_order, make_user

pytestmark = pytest.mark.db


async def test_migrations_match_the_models(db_session: AsyncSession) -> None:
    def diff(sync_conn: Connection) -> list[object]:
        return list(compare_metadata(MigrationContext.configure(sync_conn), Base.metadata))

    conn = await db_session.connection()
    assert await conn.run_sync(diff) == []
    assert await db_session.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
    assert await db_session.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))


async def test_audit_log_is_append_only(db_session: AsyncSession) -> None:
    entry = audit.record(db_session, actor_type=ActorType.SYSTEM, action="test.event")
    await db_session.flush()

    for statement in (
        "UPDATE audit_log SET action = 'tampered' WHERE id = :id",
        "DELETE FROM audit_log WHERE id = :id",
        "TRUNCATE audit_log",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            async with db_session.begin_nested():
                await db_session.execute(text(statement), {"id": entry.id})

    assert (await db_session.get(AuditLog, entry.id)) is not None


async def _return_for(session: AsyncSession) -> tuple[Return, object]:
    customer = await make_user(session)
    order = await make_order(session, customer)
    ret = Return(
        order_item_id=order.items[0].id,
        customer_id=customer.id,
        reason=ReturnReason.DEFECTIVE,
        refund_amount_cents=8900,
        status=ReturnStatus.UNDER_REVIEW,
    )
    session.add(ret)
    await session.flush()
    return ret, customer


async def test_an_automatic_denial_is_impossible(db_session: AsyncSession) -> None:
    ret, _ = await _return_for(db_session)
    ret.final_decision = Decision.DENY
    ret.decided_by_type = DeciderType.AUTO

    with pytest.raises(IntegrityError, match="denial_needs_person"):
        async with db_session.begin_nested():
            await db_session.flush()


async def test_a_person_can_deny(db_session: AsyncSession) -> None:
    ret, _ = await _return_for(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    ret.final_decision = Decision.DENY
    ret.decided_by_type = DeciderType.PERSON
    ret.decided_by_user_id = reviewer.id
    await db_session.flush()


async def test_a_review_request_goes_to_a_different_reviewer(db_session: AsyncSession) -> None:
    ret, _ = await _return_for(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    request = ReviewRequest(
        return_id=ret.id,
        customer_explanation="It was broken when it arrived.",
        original_decider_id=reviewer.id,
        assigned_reviewer_id=reviewer.id,
    )
    db_session.add(request)

    with pytest.raises(IntegrityError, match="different_reviewer"):
        async with db_session.begin_nested():
            await db_session.flush()


async def test_there_is_exactly_one_settings_row(db_session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="single_row"):
        async with db_session.begin_nested():
            await db_session.execute(text("INSERT INTO settings (id) VALUES (2)"))
