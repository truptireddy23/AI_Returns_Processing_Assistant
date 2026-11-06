"""PII removal before model steps, telemetry persistence and staff-only SSE."""

import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import AgentRun, AgentRunEvent, Order, OrderItem, Role, User
from returnguard.pipeline.checks import PolicyFacts
from returnguard.pipeline.gate import Eligibility
from returnguard.pipeline.runner import review_return
from returnguard.pipeline.steps import Case, PolicyResult, RuleSteps
from returnguard.routers import review as review_router

from .factories import make_user
from .test_pipeline import make_return
from .test_review import signed_in

pytestmark = pytest.mark.db


async def test_pipeline_masks_known_identity_and_persists_model_metadata(
    db_session: AsyncSession,
) -> None:
    ret = await make_return(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    customer.display_name = "Alice Example"
    order = await db_session.scalar(
        select(Order).join(OrderItem).where(OrderItem.id == ret.order_item_id)
    )
    assert order is not None
    order.shipping_line1 = "123 Main Street"
    ret.reason_text = f"Alice Example says she has a split seam. {customer.email}. 123 Main Street."
    seen: list[Case] = []

    class CapturingSteps(RuleSteps):
        async def policy(self, case: Case, facts: PolicyFacts) -> PolicyResult:
            seen.append(case)
            return PolicyResult(
                Eligibility.ELIGIBLE,
                ["P5"],
                "Clear",
                "model",
                {
                    "model": "test-model",
                    "prompt_version": 2,
                    "tokens_in": 100,
                    "tokens_out": 20,
                    "cost_usd": "0.00012",
                    "tool_calls": [],
                },
            )

    await review_return(db_session, ret.id, steps=CapturingSteps())
    assert seen and "split seam" in seen[0].reason_text
    for private in ("Alice", "Example", "she", customer.email, "123 Main Street"):
        assert private not in seen[0].reason_text
    run = await db_session.scalar(
        select(AgentRun).where(AgentRun.return_id == ret.id, AgentRun.step == "policy")
    )
    assert run is not None
    assert (run.model, run.prompt_version, run.tokens_in, run.tokens_out) == (
        "test-model",
        2,
        100,
        20,
    )
    assert str(run.cost_usd) == "0.000120"


async def test_trace_stream_is_staff_only_resumes_and_excludes_customer_text(
    db_session: AsyncSession,
    db_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(review_router, "TRACE_STREAM_SECONDS", 0.01)
    ret = await make_return(db_session)
    return_id = str(ret.id)
    run_id = uuid.uuid4()
    event = AgentRunEvent(
        return_id=ret.id,
        run_id=run_id,
        step="policy",
        kind="finished",
        data={"tokens_in": 42, "prompt": "PRIVATE CUSTOMER TEXT"},
    )
    db_session.add(event)
    await db_session.commit()
    event_id = event.id
    customer = await db_session.get_one(User, ret.customer_id)
    await signed_in(db_client, customer)
    assert (await db_client.get(f"/api/review/cases/{return_id}/events")).status_code == 403
    reviewer = await make_user(db_session, role=Role.REVIEWER)
    await signed_in(db_client, reviewer)
    res = await db_client.get(f"/api/review/cases/{return_id}/events")
    assert res.status_code == 200 and "text/event-stream" in res.headers["content-type"]
    assert '"tokens_in": 42' in res.text
    assert "PRIVATE" not in res.text and "prompt" not in res.text
    resumed = await db_client.get(
        f"/api/review/cases/{return_id}/events", headers={"Last-Event-ID": str(event_id)}
    )
    assert '"tokens_in"' not in resumed.text
