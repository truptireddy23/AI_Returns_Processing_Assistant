"""The reviewer decide endpoint, admin settings writes, the audit log, and a
customer's request for a second review — the M7/M8 screens this session adds
on top of the M4 pipeline."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import (
    AgreementKind,
    AgreementSample,
    AuditLog,
    Decision,
    EscalationReason,
    Return,
    ReturnStatus,
    ReviewRequest,
    ReviewRequestStatus,
    Role,
    Settings,
    User,
)

from .factories import make_user
from .test_pipeline import make_return, review, set_automation
from .test_shop_and_returns import sign_in

pytestmark = pytest.mark.db


# --- Decide -------------------------------------------------------------


async def test_reviewer_can_approve_a_clean_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)  # AI only recommends; stays in the queue
    ret = await review(db_session, await make_return(db_session))
    assert ret.ai_proposal is Decision.APPROVE

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "approve"})

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "approved"
    assert body["final_decision"] == "approve"
    assert body["decided_by_type"] == "person"

    sample = await db_session.scalar(
        select(AgreementSample).where(AgreementSample.return_id == ret.id)
    )
    assert sample is not None
    assert sample.kind is AgreementKind.AGREEMENT
    assert sample.agreed is True


async def test_reviewer_denying_a_proposed_denial_needs_no_override_reason(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session, delivered_days_ago=47))
    assert ret.status is ReturnStatus.UNDER_REVIEW  # the AI never denies (M1)
    assert ret.ai_proposal is Decision.DENY

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "deny"})

    assert res.status_code == 200, res.text
    assert res.json()["status"] == "denied"


async def test_overriding_the_ai_requires_a_reason(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))
    assert ret.ai_proposal is Decision.APPROVE

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    without_reason = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "deny"})
    assert without_reason.status_code == 422

    with_reason = await db_client.post(
        f"/api/review/{ret.id}/decide",
        json={"decision": "deny", "override_reason": "Photo doesn't match the claim."},
    )
    assert with_reason.status_code == 200, with_reason.text

    sample = await db_session.scalar(
        select(AgreementSample).where(AgreementSample.return_id == ret.id)
    )
    assert sample is not None
    assert sample.kind is AgreementKind.OVERRIDE
    assert sample.agreed is False


async def test_a_reviewer_cannot_propose_escalate_as_the_final_decision(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "escalate"})

    assert res.status_code == 422


async def test_a_decided_case_cannot_be_decided_again(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    first = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "approve"})
    assert first.status_code == 200

    second = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "approve"})

    assert second.status_code == 409


async def test_a_customer_cannot_decide_a_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))
    customer = await make_user(db_session, Role.CUSTOMER)
    await sign_in(db_client, customer)

    res = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "approve"})

    assert res.status_code == 403


async def test_case_detail_includes_the_pipeline_findings(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    ret = await review(db_session, await make_return(db_session))
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.get(f"/api/review/{ret.id}")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["case_number"] == ret.case_number
    steps = {f["step"] for f in body["findings"]}
    expected_steps = {
        "data_check",
        "policy",
        "image",
        "behavior",
        "recommendation",
        "critic",
        "gate",
    }
    assert expected_steps <= steps
    assert body["customer_history"]["past_orders"] >= 0


# --- Admin settings -----------------------------------------------------


async def test_admin_can_update_settings(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await make_user(db_session, Role.ADMIN)
    await sign_in(db_client, admin)

    res = await db_client.patch(
        "/api/admin/settings",
        json={"automation_enabled": True, "high_value_limit_cents": 30000},
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["automation_enabled"] is True
    assert body["high_value_limit_cents"] == 30000

    row = await db_session.get_one(Settings, 1, populate_existing=True)
    assert row.automation_enabled is True
    assert row.updated_by_user_id == admin.id

    entry = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "admin.settings_updated")
    )
    assert entry is not None


async def test_settings_update_rejects_an_out_of_range_value(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await make_user(db_session, Role.ADMIN)
    await sign_in(db_client, admin)

    res = await db_client.patch("/api/admin/settings", json={"risk_limit": "1.50"})

    assert res.status_code == 422


async def test_a_reviewer_cannot_update_settings(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.patch("/api/admin/settings", json={"automation_enabled": True})

    assert res.status_code == 403


# --- Audit log ------------------------------------------------------------


async def test_admin_can_list_and_filter_the_audit_log(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=True)
    ret = await review(db_session, await make_return(db_session))
    admin = await make_user(db_session, Role.ADMIN)
    await sign_in(db_client, admin)

    res = await db_client.get("/api/admin/audit-log", params={"return_id": str(ret.id)})

    assert res.status_code == 200, res.text
    rows = res.json()
    assert rows
    assert all(r["return_id"] == str(ret.id) for r in rows)


async def test_a_reviewer_cannot_read_the_audit_log(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)

    res = await db_client.get("/api/admin/audit-log")

    assert res.status_code == 403


# --- Request a review (S2) ------------------------------------------------


async def _deny_a_return(
    db_session: AsyncSession, db_client: httpx.AsyncClient
) -> tuple[Return, User, User]:
    await set_automation(db_session, on=True)
    customer = await make_user(db_session, Role.CUSTOMER)
    ret = await review(
        db_session, await make_return(db_session, customer=customer, delivered_days_ago=47)
    )
    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    res = await db_client.post(
        f"/api/review/{ret.id}/decide",
        json={"decision": "deny", "override_reason": "Outside the return window."},
    )
    assert res.status_code == 200, res.text
    return ret, reviewer, customer


async def test_customer_can_request_a_review_of_a_denial(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret, _reviewer, customer = await _deny_a_return(db_session, db_client)
    await sign_in(db_client, customer)

    res = await db_client.post(
        f"/api/returns/{ret.id}/review-requests", json={"explanation": "I think this is wrong."}
    )

    assert res.status_code == 201, res.text
    assert res.json()["status"] == "under_review"

    rr = await db_session.scalar(select(ReviewRequest).where(ReviewRequest.return_id == ret.id))
    assert rr is not None
    assert rr.status is ReviewRequestStatus.OPEN

    fresh = await db_session.get_one(Return, ret.id, populate_existing=True)
    assert fresh.escalation_reason is EscalationReason.CUSTOMER_REQUESTED_REVIEW


async def test_cannot_request_a_review_of_a_non_denied_return(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await set_automation(db_session, on=False)
    customer = await make_user(db_session, Role.CUSTOMER)
    ret = await review(db_session, await make_return(db_session, customer=customer))
    await sign_in(db_client, customer)

    res = await db_client.post(
        f"/api/returns/{ret.id}/review-requests", json={"explanation": "..."}
    )

    assert res.status_code == 409


async def test_the_original_decider_cannot_redecide_after_a_review_request(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret, original_reviewer, customer = await _deny_a_return(db_session, db_client)
    await sign_in(db_client, customer)
    await db_client.post(
        f"/api/returns/{ret.id}/review-requests", json={"explanation": "Please look again."}
    )

    await sign_in(db_client, original_reviewer)
    blocked = await db_client.post(f"/api/review/{ret.id}/decide", json={"decision": "approve"})
    assert blocked.status_code == 403

    other_reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, other_reviewer)
    allowed = await db_client.post(
        f"/api/review/{ret.id}/decide",
        json={
            "decision": "approve",
            # Still disagreeing with the AI's original proposal (DENY), which
            # is what override_reason is required for — not with the first
            # reviewer's decision specifically.
            "override_reason": "Customer's review request raised a valid point.",
        },
    )
    assert allowed.status_code == 200, allowed.text

    rr = await db_session.scalar(select(ReviewRequest).where(ReviewRequest.return_id == ret.id))
    assert rr is not None
    assert rr.status is ReviewRequestStatus.RESOLVED
    assert rr.assigned_reviewer_id == other_reviewer.id
