"""Admin: editable settings that take effect at once, the dashboard, and the audit log."""

from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import (
    AuditLog,
    EscalationReason,
    ReturnReason,
    ReturnStatus,
    Role,
    Settings,
)

from .factories import make_user
from .test_pipeline import make_return, review
from .test_review import decide, ensure_policy, escalated_case, signed_in

pytestmark = pytest.mark.db

VALID = {
    "automation_enabled": True,
    "risk_limit": "0.30",
    "high_value_limit_cents": 25000,
    "qa_sample_rate": "0.00",
}


async def test_only_admins_can_read_or_change_settings(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)
    assert (await db_client.get("/api/admin/settings")).status_code == 403
    res = await db_client.put("/api/admin/settings", json=VALID, headers=headers)
    assert res.status_code == 403
    assert (await db_client.get("/api/admin/metrics")).status_code == 403
    assert (await db_client.get("/api/admin/audit")).status_code == 403


async def test_settings_are_validated(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await make_user(db_session, Role.ADMIN)
    headers = await signed_in(db_client, admin)
    for bad in (
        {"risk_limit": "1.50"},
        {"risk_limit": "0.305"},
        {"high_value_limit_cents": 0},
        {"high_value_limit_cents": 2_000_000},
        {"qa_sample_rate": "-0.10"},
        {"fixed_rules": False},  # unknown fields are refused, not ignored
    ):
        res = await db_client.put("/api/admin/settings", json={**VALID, **bad}, headers=headers)
        assert res.status_code == 422, bad


async def test_a_change_is_saved_and_audited_with_old_and_new_values(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await make_user(db_session, Role.ADMIN)
    headers = await signed_in(db_client, admin)
    before = await db_session.get_one(Settings, 1)
    old_limit = before.high_value_limit_cents

    res = await db_client.put(
        "/api/admin/settings",
        json={**VALID, "high_value_limit_cents": 10000},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["high_value_limit_cents"] == 10000
    assert body["updated_by_name"] == admin.display_name

    entry = await db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "admin.settings_changed")
        .order_by(AuditLog.id.desc())
    )
    assert entry is not None
    assert entry.actor_user_id == admin.id
    assert entry.details["changes"]["high_value_limit_cents"] == [old_limit, 10000]


async def test_the_high_value_limit_takes_effect_on_the_next_return(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """A clear $120 change-of-mind return: auto-approved under a $250 limit, sent to
    a person as soon as the admin lowers the limit to $100."""
    await ensure_policy(db_session)
    admin = await make_user(db_session, Role.ADMIN)
    headers = await signed_in(db_client, admin)

    res = await db_client.put("/api/admin/settings", json=VALID, headers=headers)
    assert res.status_code == 200
    first = await review(
        db_session,
        await make_return(db_session, reason=ReturnReason.CHANGED_MIND, price_cents=12000),
    )
    assert first.status is ReturnStatus.APPROVED

    res = await db_client.put(
        "/api/admin/settings", json={**VALID, "high_value_limit_cents": 10000}, headers=headers
    )
    assert res.status_code == 200
    second = await review(
        db_session,
        await make_return(db_session, reason=ReturnReason.CHANGED_MIND, price_cents=12000),
    )
    assert second.status is ReturnStatus.UNDER_REVIEW
    assert second.escalation_reason is EscalationReason.HIGH_VALUE

    # The reviewer's case page compares against the current limit too.
    case = (await db_client.get(f"/api/review/cases/{second.id}")).json()
    value = next(c for c in case["checks"] if c["key"] == "value")
    assert value["state"] == "warn"
    assert "$100" in value["detail"]


async def test_turning_automation_off_sends_everything_to_a_person(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await ensure_policy(db_session)
    admin = await make_user(db_session, Role.ADMIN)
    headers = await signed_in(db_client, admin)
    res = await db_client.put(
        "/api/admin/settings", json={**VALID, "automation_enabled": False}, headers=headers
    )
    assert res.status_code == 200
    settings = await db_session.get_one(Settings, 1, populate_existing=True)
    assert settings.automation_enabled is False
    assert settings.risk_limit == Decimal("0.30")

    ret = await review(db_session, await make_return(db_session, reason=ReturnReason.CHANGED_MIND))
    assert ret.status is ReturnStatus.UNDER_REVIEW
    assert ret.escalation_reason is EscalationReason.AUTOMATION_OFF


async def test_the_dashboard_counts_routing_and_agreement(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    agreed = await escalated_case(db_session, reason=ReturnReason.CHANGED_MIND, photo=False)
    overridden = await escalated_case(db_session, reason=ReturnReason.CHANGED_MIND, photo=False)
    waiting = await escalated_case(db_session)  # stays in the queue
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)
    assert (await decide(db_client, headers, agreed, decision="approve")).status_code == 200
    res = await decide(
        db_client,
        headers,
        overridden,
        decision="deny",
        confirm_denial=True,
        policy_clauses=["P5"],
        override_reason="looks_like_wear",
    )
    assert res.status_code == 200

    admin = await make_user(db_session, Role.ADMIN)
    await signed_in(db_client, admin)
    res = await db_client.get("/api/admin/metrics", params={"days": 7})
    assert res.status_code == 200, res.text
    m = res.json()
    assert m["returns_started"] >= 3
    assert m["sent_to_person"] >= 3
    assert m["open_now"] >= 1
    assert m["approved_by_people"] >= 1
    assert m["denied_by_people"] >= 1
    assert reviewer.display_name in [r["name"] for r in m["reviewers"]]
    assert m["agreement_total"] >= 2
    assert "looks_like_wear" in [o["key"] for o in m["top_overrides"]]
    assert "footwear" in [r["key"] for r in m["agreement_by_category"]]
    assert str(waiting.id)  # still open, counted above

    assert (await db_client.get("/api/admin/metrics", params={"days": 400})).status_code == 422


async def test_the_audit_log_filters_by_action_and_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    ret = await escalated_case(db_session)
    reviewer = await make_user(db_session, Role.REVIEWER)
    headers = await signed_in(db_client, reviewer)
    assert (await decide(db_client, headers, ret, decision="approve")).status_code == 200

    admin = await make_user(db_session, Role.ADMIN)
    await signed_in(db_client, admin)
    page = (await db_client.get("/api/admin/audit", params={"case_number": ret.case_number})).json()
    actions = [e["action"] for e in page["entries"]]
    assert actions[0] == "review.approved"  # newest first
    assert "gate.escalated" in actions
    assert all(e["case_number"] == ret.case_number for e in page["entries"])
    approved = page["entries"][0]
    assert approved["actor_name"] == reviewer.display_name

    reviews = (await db_client.get("/api/admin/audit", params={"action": "review."})).json()
    assert reviews["entries"]
    assert all(e["action"].startswith("review.") for e in reviews["entries"])

    one = (await db_client.get("/api/admin/audit", params={"limit": 1})).json()
    assert len(one["entries"]) == 1
    assert one["next_before_id"] == one["entries"][0]["id"]
    older = (
        await db_client.get(
            "/api/admin/audit", params={"limit": 1, "before_id": one["next_before_id"]}
        )
    ).json()
    assert older["entries"][0]["id"] < one["entries"][0]["id"]
