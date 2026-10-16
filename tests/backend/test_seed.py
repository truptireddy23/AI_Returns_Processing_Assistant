from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import addresses, seed
from returnguard.config import Settings
from returnguard.models import (
    DeciderType,
    Decision,
    Order,
    PolicyChunk,
    PolicyDoc,
    Product,
    Return,
    Role,
    User,
)

from .conftest import SEED_DIR

pytestmark = pytest.mark.db

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=UTC)


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_seed_loads_everything_once(db_session: AsyncSession) -> None:
    first = await seed.seed(db_session, SEED_DIR, now=NOW)
    second = await seed.seed(db_session, SEED_DIR, now=NOW)

    assert not first.skipped
    assert second.skipped
    assert first.users == await _count(db_session, User) == 10
    assert first.products == await _count(db_session, Product) == 20
    assert first.orders == await _count(db_session, Order)
    assert first.returns == await _count(db_session, Return)

    roles = (await db_session.scalars(select(User.role))).all()
    assert roles.count(Role.REVIEWER) == 2
    assert roles.count(Role.ADMIN) == 1

    policy = (await db_session.scalars(select(PolicyDoc).where(PolicyDoc.is_active))).one()
    assert policy.version == 1
    clauses = await db_session.scalar(
        select(func.count()).select_from(PolicyChunk).where(PolicyChunk.policy_doc_id == policy.id)
    )
    assert clauses == 9


async def test_seeded_denials_were_all_made_by_a_person(db_session: AsyncSession) -> None:
    await seed.seed(db_session, SEED_DIR, now=NOW)
    denials = (
        await db_session.scalars(select(Return).where(Return.final_decision == Decision.DENY))
    ).all()
    assert denials
    assert all(r.decided_by_type == DeciderType.PERSON for r in denials)


async def test_seed_includes_two_accounts_sharing_an_address(db_session: AsyncSession) -> None:
    await seed.seed(db_session, SEED_DIR, now=NOW)
    shared = await db_session.scalars(
        select(Order.address_fingerprint)
        .group_by(Order.address_fingerprint)
        .having(func.count(func.distinct(Order.customer_id)) > 1)
    )
    assert len(shared.all()) == 1


def test_address_fingerprint_ignores_case_spacing_and_punctuation() -> None:
    a = addresses.fingerprint("1200 W Springfield Ave", "Champaign", "61821")
    b = addresses.fingerprint("1200  w. Springfield Ave", "CHAMPAIGN", "61821")
    c = addresses.fingerprint("1201 W Springfield Ave", "Champaign", "61821")
    assert a == b != c


async def test_seed_refuses_to_run_in_production(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    production = Settings(environment="production", cookie_secure=True)
    monkeypatch.setattr(seed, "get_settings", lambda: production)
    with pytest.raises(RuntimeError, match="production"):
        await seed.seed(db_session, SEED_DIR)
