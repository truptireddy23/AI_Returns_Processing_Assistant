"""The reviewer flow (M7): queue, case page, claims, decisions, and review requests."""

from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import (
    AgreementKind,
    AgreementSample,
    AuditLog,
    DeciderType,
    Decision,
    EscalationReason,
    PolicyChunk,
    PolicyDoc,
    Return,
    ReturnReason,
    ReturnStatus,
    ReviewRequest,
    ReviewRequestStatus,
    Role,
    User,
)

from .factories import PASSWORD, make_user
from .test_auth import login
from .test_pipeline import make_return, review, set_automation

pytestmark = pytest.mark.db


async def ensure_policy(session: AsyncSession) -> None:
    """An active policy with clauses P1-P9 (the test database isn't seeded)."""
    if await session.scalar(select(PolicyDoc).where(PolicyDoc.is_active)):
        return
    doc = PolicyDoc(
        version=9001, title="Test policy", effective_date=date(2026, 9, 1), is_active=True
    )
    doc.chunks = [
        PolicyChunk(clause_id=f"P{i}", title=f"Clause {i}", body=f"Body of clause {i}.")
        for i in range(1, 10)
    ]
    session.add(doc)
    await session.flush()


async def escalated_case(
    session: AsyncSession,
    *,
    reason: ReturnReason = ReturnReason.DAMAGED,
    photo: bool = True,
    automation: bool = False,
    delivered_days_ago: int = 5,
    customer: User | None = None,
) -> Return:
    """A return the pipeline sent to a person."""
    await ensure_policy(session)
    await set_automation(session, automation, qa="0")
    ret = await make_return(
        session,
        customer=customer,
        reason=reason,
        photo=photo,
        delivered_days_ago=delivered_days_ago,
    )
    ret = await review(session, ret)
    assert ret.status is ReturnStatus.UNDER_REVIEW
    return ret


async def signed_in(client: httpx.AsyncClient, user: User) -> dict[str, str]:
    res = await login(client, user.email, PASSWORD)
    assert res.status_code == 200, res.text
    return {"X-CSRF-Token": res.json()["csrf_token"]}


async def decide(
    client: httpx.AsyncClient, headers: dict[str, str], ret: Return, **body: object
) -> httpx.Response:
    return await client.post(f"/api/review/cases/{ret.id}/decision", json=body, headers=headers)


# --- Access and the queue ----------------------------------------------------


async def test_only_staff_can_see_the_queue_and_cases(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    await signed_in(db_client, customer)
    assert (await db_client.get("/api/review/queue")).status_code == 403
    assert (await db_client.get(f"/api/review/cases/{ret.id}")).status_code == 403


async def test_the_queue_names_why_each_case_is_there(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    await signed_in(db_client, reviewer)

    items = (await db_client.get("/api/review/queue")).json()
    row = next(i for i in items if i["id"] == str(ret.id))
    assert row["product_name"] == "Test Sneaker"
    assert row["escalation_reason"] == EscalationReason.UNVERIFIED_PHOTO.value
    assert row["evidence_strength"] == "weak"
    assert row["claimed_by_name"] is None


async def test_the_case_page_shows_the_evidence_but_not_who_the_customer_is(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    reviewer = await make_user(db_session, Role.REVIEWER)
    await signed_in(db_client, reviewer)

    res = await db_client.get(f"/api/review/cases/{ret.id}")
    assert res.status_code == 200
    case = res.json()
    checks = {c["key"]: c for c in case["checks"]}
    assert checks["window"]["state"] == "pass"
    assert checks["photo"]["state"] == "warn"  # not verified
    assert {c["clause_id"] for c in case["clauses"] if c["cited"]} >= {"P1", "P2", "P4"}
    assert case["ai"]["proposal"] == "escalate"
    assert case["can_decide"] is True
    assert [e["action"] for e in case["timeline"]][-1] == "gate.escalated"
    # Bias safeguard: no name or email reaches the case page.
    assert customer.email not in res.text
    assert customer.display_name not in res.text


# --- Decisions ---------------------------------------------------------------


async def test_a_reviewer_approves_an_escalated_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    res = await decide(db_client, headers, ret, decision="approve")
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "approved"

    saved = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert saved.final_decision is Decision.APPROVE
    assert saved.decided_by_type is DeciderType.PERSON
    assert saved.decided_by_user_id == reviewer.id
    assert saved.customer_message and "approved by a member of our team" in saved.customer_message
    actions = await db_session.scalars(select(AuditLog.action).where(AuditLog.return_id == ret.id))
    assert "review.approved" in list(actions)
    # The AI only escalated, so there's no approve/deny proposal to agree with.
    assert (
        await db_session.scalar(select(AgreementSample).where(AgreementSample.return_id == ret.id))
        is None
    )


async def test_a_denial_needs_confirmation_and_a_policy_rule(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    unconfirmed = await decide(db_client, headers, ret, decision="deny", policy_clauses=["P3"])
    assert unconfirmed.status_code == 422
    no_rule = await decide(db_client, headers, ret, decision="deny", confirm_denial=True)
    assert no_rule.status_code == 422
    made_up = await decide(
        db_client, headers, ret, decision="deny", confirm_denial=True, policy_clauses=["P99"]
    )
    assert made_up.status_code == 422

    res = await decide(
        db_client, headers, ret, decision="deny", confirm_denial=True, policy_clauses=["P3"]
    )
    assert res.status_code == 200, res.text
    saved = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert saved.status is ReturnStatus.DENIED
    assert saved.decided_by_type is DeciderType.PERSON
    assert saved.customer_message is not None
    assert "P3" in saved.customer_message
    assert "request a review" in saved.customer_message


async def test_disagreeing_with_the_ai_needs_a_reason_and_is_recorded(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    # A clear change-of-mind return with automation off: the AI proposes approve.
    ret = await escalated_case(db_session, reason=ReturnReason.CHANGED_MIND, photo=False)
    assert ret.ai_proposal is Decision.APPROVE
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    no_reason = await decide(
        db_client, headers, ret, decision="deny", confirm_denial=True, policy_clauses=["P5"]
    )
    assert no_reason.status_code == 422

    other_without_note = await decide(
        db_client,
        headers,
        ret,
        decision="deny",
        confirm_denial=True,
        policy_clauses=["P5"],
        override_reason="other",
    )
    assert other_without_note.status_code == 422

    res = await decide(
        db_client,
        headers,
        ret,
        decision="deny",
        confirm_denial=True,
        policy_clauses=["P5"],
        override_reason="looks_like_wear",
    )
    assert res.status_code == 200, res.text
    sample = await db_session.scalar(
        select(AgreementSample).where(AgreementSample.return_id == ret.id)
    )
    assert sample is not None
    assert sample.kind is AgreementKind.OVERRIDE
    assert sample.agreed is False
    assert sample.override_reason == "looks_like_wear"
    assert sample.escalation_reason is EscalationReason.AUTOMATION_OFF


async def test_agreeing_with_the_ai_is_recorded_too(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session, reason=ReturnReason.CHANGED_MIND, photo=False)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)

    res = await decide(db_client, headers, ret, decision="approve")
    assert res.status_code == 200, res.text
    sample = await db_session.scalar(
        select(AgreementSample).where(AgreementSample.return_id == ret.id)
    )
    assert sample is not None
    assert sample.agreed is True
    assert sample.kind is AgreementKind.AGREEMENT


async def test_a_case_is_decided_only_once(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)
    assert (await decide(db_client, headers, ret, decision="approve")).status_code == 200
    again = await decide(
        db_client, headers, ret, decision="deny", confirm_denial=True, policy_clauses=["P3"]
    )
    assert again.status_code == 409


# --- Claims ------------------------------------------------------------------


async def test_a_claimed_case_is_locked_to_its_reviewer_until_the_claim_goes_stale(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    riley = await make_user(db_session, Role.REVIEWER)
    sam = await make_user(db_session, Role.REVIEWER)

    riley_headers = await signed_in(db_client, riley)
    claimed = await db_client.post(f"/api/review/cases/{ret.id}/claim", headers=riley_headers)
    assert claimed.status_code == 200
    assert claimed.json()["claimed_by_me"] is True

    sam_headers = await signed_in(db_client, sam)
    case = (await db_client.get(f"/api/review/cases/{ret.id}")).json()
    assert case["can_decide"] is False
    assert case["claimed_by_name"] == riley.display_name
    steal = await db_client.post(f"/api/review/cases/{ret.id}/claim", headers=sam_headers)
    assert steal.status_code == 409
    blocked = await decide(db_client, sam_headers, ret, decision="approve")
    assert blocked.status_code == 409

    # An abandoned claim stops blocking after the time limit.
    saved = await db_session.get_one(Return, ret.id, populate_existing=True)
    saved.claimed_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.flush()
    assert (await decide(db_client, sam_headers, ret, decision="approve")).status_code == 200


async def test_releasing_a_claim_returns_the_case_to_the_queue(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)
    await db_client.post(f"/api/review/cases/{ret.id}/claim", headers=headers)
    row = await queue_row(db_client, ret)
    assert row["claimed_by_me"] is True

    released = await db_client.delete(f"/api/review/cases/{ret.id}/claim", headers=headers)
    assert released.json()["claimed_by_name"] is None
    row = await queue_row(db_client, ret)
    assert row["claimed_by_name"] is None


async def queue_row(client: httpx.AsyncClient, ret: Return) -> dict[str, object]:
    items = (await client.get("/api/review/queue")).json()
    row: dict[str, object] = next(i for i in items if i["id"] == str(ret.id))
    return row


async def test_decided_by_me_lists_only_my_final_decisions(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    approved = await escalated_case(db_session)
    denied = await escalated_case(db_session)
    someone_elses = await escalated_case(db_session)
    me = await make_user(db_session, Role.REVIEWER)
    other = await make_user(db_session, Role.REVIEWER)

    headers = await signed_in(db_client, other)
    assert (await decide(db_client, headers, someone_elses, decision="approve")).status_code == 200

    headers = await signed_in(db_client, me)
    assert (await decide(db_client, headers, approved, decision="approve")).status_code == 200
    res = await decide(
        db_client, headers, denied, decision="deny", confirm_denial=True, policy_clauses=["P3"]
    )
    assert res.status_code == 200

    mine = (await db_client.get("/api/review/queue", params={"view": "decided_by_me"})).json()
    assert {i["id"]: i["final_decision"] for i in mine} == {
        str(approved.id): "approve",
        str(denied.id): "deny",
    }
    assert all(i["decided_by_name"] == me.display_name for i in mine)
    # Newest first.
    assert mine[0]["id"] == str(denied.id)

    # A denial the customer asks to have reviewed isn't final any more.
    customer = await db_session.get_one(User, denied.customer_id)
    customer_headers = await signed_in(db_client, customer)
    await db_client.post(
        f"/api/returns/{denied.id}/review-request",
        json={"explanation": "It was broken when it arrived, please look again."},
        headers=customer_headers,
    )
    await signed_in(db_client, me)
    mine = (await db_client.get("/api/review/queue", params={"view": "decided_by_me"})).json()
    assert [i["id"] for i in mine] == [str(approved.id)]


# --- Review requests ---------------------------------------------------------


async def test_a_customer_can_ask_for_a_different_reviewer_to_look_again(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    first = await make_user(db_session, Role.REVIEWER)
    second = await make_user(db_session, Role.REVIEWER)

    headers = await signed_in(db_client, first)
    denied = await decide(
        db_client, headers, ret, decision="deny", confirm_denial=True, policy_clauses=["P3"]
    )
    assert denied.status_code == 200
    gate_reason = ret.escalation_reason
    assert gate_reason is not None
    samples_after_first_decision = len(
        list(
            await db_session.scalars(
                select(AgreementSample).where(AgreementSample.return_id == ret.id)
            )
        )
    )

    # The customer sees the denial and may ask once.
    customer_headers = await signed_in(db_client, customer)
    view = (await db_client.get(f"/api/returns/{ret.id}")).json()
    assert view["status"] == "denied"
    assert view["can_request_review"] is True
    too_short = await db_client.post(
        f"/api/returns/{ret.id}/review-request",
        json={"explanation": "no"},
        headers=customer_headers,
    )
    assert too_short.status_code == 422
    res = await db_client.post(
        f"/api/returns/{ret.id}/review-request",
        json={"explanation": "The seam split after two days of normal use."},
        headers=customer_headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "under_review"
    assert res.json()["can_request_review"] is False
    assert res.json()["review_request_status"] == "open"
    again = await db_client.post(
        f"/api/returns/{ret.id}/review-request",
        json={"explanation": "Please look again, it really is a defect."},
        headers=customer_headers,
    )
    assert again.status_code == 409

    # The row keeps the gate's reason (for the metrics); the review screens show why
    # the case is back.
    saved = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert saved.escalation_reason is gate_reason
    assert saved.final_decision is None
    queue = await db_client.get("/api/review/queue", headers=await signed_in(db_client, second))
    [item] = [i for i in queue.json() if i["id"] == str(ret.id)]
    assert item["escalation_reason"] == "customer_requested_review"

    # The reviewer who denied it can't decide the review...
    headers = await signed_in(db_client, first)
    case = (await db_client.get(f"/api/review/cases/{ret.id}")).json()
    assert case["escalation_reason"] == "customer_requested_review"
    assert case["can_decide"] is False
    assert case["review_request"]["original_decider_is_me"] is True
    assert (await decide(db_client, headers, ret, decision="approve")).status_code == 409

    # ...a different one can.
    headers = await signed_in(db_client, second)
    res = await decide(db_client, headers, ret, decision="approve")
    assert res.status_code == 200, res.text
    rr = await db_session.scalar(select(ReviewRequest).where(ReviewRequest.return_id == ret.id))
    assert rr is not None
    await db_session.refresh(rr)
    assert rr.status is ReviewRequestStatus.RESOLVED
    assert rr.assigned_reviewer_id == second.id
    assert rr.outcome is Decision.APPROVE

    # The re-review is recorded on the request, not as a second agreement sample.
    samples = await db_session.scalars(
        select(AgreementSample).where(AgreementSample.return_id == ret.id)
    )
    assert len(list(samples)) == samples_after_first_decision
    case = (await db_client.get(f"/api/review/cases/{ret.id}")).json()
    assert case["escalation_reason"] == gate_reason.value


async def test_only_the_owner_can_request_a_review_of_a_denial(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    customer = await db_session.get_one(User, ret.customer_id)
    stranger = await make_user(db_session)
    body = {"explanation": "Please look at this again, thank you."}

    # Not denied yet.
    headers = await signed_in(db_client, customer)
    res = await db_client.post(f"/api/returns/{ret.id}/review-request", json=body, headers=headers)
    assert res.status_code == 409

    # Someone else's return looks the same as a missing one.
    headers = await signed_in(db_client, stranger)
    res = await db_client.post(f"/api/returns/{ret.id}/review-request", json=body, headers=headers)
    assert res.status_code == 404
