"""The demo-case loader builds each customer's story and queues a real review."""

import random
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from returnguard import demo_cases
from returnguard.models import (
    AgentRun,
    Job,
    Order,
    OrderItem,
    Return,
    ReturnMessage,
    ReturnPhoto,
    ReturnStatus,
    User,
)
from returnguard.pipeline.behavior import BehaviorInputs, score_behavior
from returnguard.pipeline.gate import Eligibility
from returnguard.pipeline.runner import behavior_inputs, review_return
from returnguard.pipeline.steps import RuleSteps
from returnguard.seed import seed

from .conftest import SEED_DIR

pytestmark = pytest.mark.db


class NoSample(random.Random):
    def random(self) -> float:
        return 0.999


def _cases() -> dict[str, dict[str, object]]:
    return {c["key"]: c for c in demo_cases._load_cases(SEED_DIR)}


async def _load(db_session: AsyncSession) -> dict[str, Return]:
    await seed(db_session, SEED_DIR)  # reviewers, products, policy, Casey and Quinn
    now = datetime.now(UTC)
    out = {}
    for case in demo_cases._load_cases(SEED_DIR):
        loaded = await demo_cases.load_case(db_session, SEED_DIR, case, now=now)
        assert not loaded.skipped
        ret = await db_session.scalar(
            select(Return).where(Return.case_number == loaded.case_number)
        )
        assert ret is not None
        out[case["key"]] = ret
    return out


async def _inputs(db_session: AsyncSession, ret: Return) -> BehaviorInputs:
    item = await db_session.scalar(
        select(OrderItem)
        .where(OrderItem.id == ret.order_item_id)
        .options(selectinload(OrderItem.order))
    )
    assert item is not None
    user = await db_session.get_one(User, ret.customer_id)
    return await behavior_inputs(db_session, ret, item.order, user, 25000)


async def test_each_case_gets_its_own_account_age_and_history(db_session: AsyncSession) -> None:
    returns = await _load(db_session)
    cases = _cases()
    assert len(returns) == 6
    now = datetime.now(UTC)
    for key, ret in returns.items():
        case = cases[key]
        user = await db_session.get_one(User, ret.customer_id)
        assert abs((now - user.created_at).days - case["account_age_days"]) <= 1  # type: ignore[operator]
        history = case["history"]
        assert isinstance(history, dict)
        orders = await db_session.scalar(
            select(func.count()).select_from(Order).where(Order.customer_id == user.id)
        )
        assert orders == history["orders"] + 1  # plus the order being returned
        past = await db_session.scalar(
            select(func.count())
            .select_from(Return)
            .where(Return.customer_id == user.id, Return.id != ret.id)
        )
        assert past == history["approved_returns"] + history["denied_returns"]
        # No past order predates the account.
        first = await db_session.scalar(
            select(func.min(Order.placed_at)).where(Order.customer_id == user.id)
        )
        assert first is not None and first >= user.created_at
        assert ret.status is ReturnStatus.SUBMITTED
        assert await db_session.scalar(select(Job).where(Job.return_id == ret.id))
        photos = await db_session.scalar(
            select(func.count()).select_from(ReturnPhoto).where(ReturnPhoto.return_id == ret.id)
        )
        spec = case["return"]
        assert isinstance(spec, dict)
        assert photos == (1 if spec["photo"] else 0)


async def test_refunds_follow_the_item_and_quantity(db_session: AsyncSession) -> None:
    returns = await _load(db_session)
    # Two-item order: only the sweater ($72) is refunded.
    last_day = returns["last_day"]
    item = await db_session.get_one(OrderItem, last_day.order_item_id)
    order = await db_session.get_one(Order, item.order_id)
    assert last_day.refund_amount_cents == 7200
    assert order.total_cents > last_day.refund_amount_cents
    # Four packs of tees at $35.
    assert returns["bulk_with_chat"].refund_amount_cents == 4 * 3500


async def test_the_bulk_case_has_a_customer_question_waiting(db_session: AsyncSession) -> None:
    returns = await _load(db_session)
    message = await db_session.scalar(
        select(ReturnMessage).where(ReturnMessage.return_id == returns["bulk_with_chat"].id)
    )
    assert message is not None
    assert message.sender_user_id == returns["bulk_with_chat"].customer_id


async def test_the_risk_scores_tell_the_stories(db_session: AsyncSession) -> None:
    returns = await _load(db_session)
    ring = await _inputs(db_session, returns["address_ring"])
    assert ring.other_accounts_at_address == 2  # Casey and Quinn
    assert ring.recent_returns_30d == 2
    assert score_behavior(ring).score >= 0.5  # well above the 0.30 limit
    assert score_behavior(await _inputs(db_session, returns["last_day"])).score < 0.1


async def test_day_30_is_still_inside_the_window(db_session: AsyncSession) -> None:
    returns = await _load(db_session)
    ret = returns["last_day"]
    await review_return(db_session, ret.id, steps=RuleSteps(), rng=NoSample())
    saved = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert saved.status is ReturnStatus.UNDER_REVIEW  # automation is off by default
    policy = await db_session.scalar(
        select(AgentRun).where(AgentRun.return_id == ret.id, AgentRun.step == "policy")
    )
    assert policy is not None and policy.output is not None
    assert policy.output["eligibility"] == Eligibility.ELIGIBLE.value
    assert "day 30 of 30" in policy.output["reason"]


async def test_loading_twice_skips_existing_customers(db_session: AsyncSession) -> None:
    await _load(db_session)
    case = _cases()["last_day"]
    again = await demo_cases.load_case(db_session, SEED_DIR, case, now=datetime.now(UTC))
    assert again.skipped
