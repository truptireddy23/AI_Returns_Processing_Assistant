"""Code-only pipeline rules: data check, policy facts, behaviour risk, and the gate."""

import random
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from returnguard.models import Decision, EscalationReason, EvidenceStrength, ReturnReason, Route
from returnguard.pipeline.behavior import WEIGHTS, BehaviorInputs, score_behavior
from returnguard.pipeline.checks import data_check, days_since_delivery, policy_facts
from returnguard.pipeline.gate import (
    Eligibility,
    GateInputs,
    GateResult,
    GateSettings,
    PhotoCheck,
    governance_gate,
)

# --- Data check -------------------------------------------------------------


def test_complete_requests_pass() -> None:
    assert data_check(reason=ReturnReason.DEFECTIVE, photo_count=1, delivered=True).complete
    assert data_check(reason=ReturnReason.CHANGED_MIND, photo_count=0, delivered=True).complete


@pytest.mark.parametrize(
    "reason",
    [
        ReturnReason.DAMAGED,
        ReturnReason.DEFECTIVE,
        ReturnReason.WRONG_ITEM,
        ReturnReason.NOT_AS_DESCRIBED,
    ],
)
def test_a_missing_photo_goes_back_to_the_customer(reason: ReturnReason) -> None:
    result = data_check(reason=reason, photo_count=0, delivered=True)
    assert not result.complete
    assert result.missing == ["photo"]
    assert result.customer_message == "We need a photo of the problem to continue."


# --- Policy facts (code, not the model) --------------------------------------


def chicago(y: int, m: int, d: int, h: int = 12) -> datetime:
    from zoneinfo import ZoneInfo

    return datetime(y, m, d, h, tzinfo=ZoneInfo("America/Chicago"))


@pytest.mark.parametrize(("days", "within"), [(0, True), (30, True), (31, False)])
def test_return_window_edges(days: int, within: bool) -> None:
    delivered = chicago(2026, 9, 1)
    requested = chicago(2026, 9, 1 + days) if days < 30 else chicago(2026, 10, days - 29)
    facts = policy_facts(
        reason=ReturnReason.CHANGED_MIND,
        delivered_at=delivered,
        requested_at=requested,
        is_final_sale=False,
        refund_cents=1000,
        high_value_limit_cents=25000,
    )
    assert facts.days_since_delivery == days
    assert facts.within_window is within
    assert ("P1" in facts.blocking_clauses()) is not within


def test_days_are_counted_in_shop_time_not_utc() -> None:
    # 11:30 pm in Chicago on Sep 1 is already Sep 2 in UTC; it's still day 0.
    delivered = chicago(2026, 9, 1, 23)
    requested = datetime(2026, 9, 2, 4, 45, tzinfo=UTC)  # 11:45 pm Sep 1 in Chicago
    assert days_since_delivery(delivered, requested) == 0


@pytest.mark.parametrize(
    ("reason", "blocks"),
    [
        (ReturnReason.CHANGED_MIND, True),
        (ReturnReason.NOT_AS_DESCRIBED, True),
        (ReturnReason.DAMAGED, False),
        (ReturnReason.DEFECTIVE, False),
        (ReturnReason.WRONG_ITEM, False),
    ],
)
def test_final_sale_rule(reason: ReturnReason, blocks: bool) -> None:
    facts = policy_facts(
        reason=reason,
        delivered_at=chicago(2026, 10, 1),
        requested_at=chicago(2026, 10, 3),
        is_final_sale=True,
        refund_cents=1000,
        high_value_limit_cents=25000,
    )
    assert facts.final_sale_blocks is blocks


def test_high_value_is_strictly_above_the_limit() -> None:
    def fact(cents: int) -> bool:
        return policy_facts(
            reason=ReturnReason.DEFECTIVE,
            delivered_at=chicago(2026, 10, 1),
            requested_at=chicago(2026, 10, 2),
            is_final_sale=False,
            refund_cents=cents,
            high_value_limit_cents=25000,
        ).high_value

    assert fact(25000) is False
    assert fact(25001) is True


# --- Behaviour risk ---------------------------------------------------------

BASE = BehaviorInputs(
    past_orders=15,
    past_returns=1,
    recent_returns_30d=0,
    account_age_days=1000,
    other_accounts_at_address=0,
    refund_cents=8900,
    high_value_limit_cents=25000,
)


def test_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_an_established_clean_customer_is_low_risk() -> None:
    assert score_behavior(BASE).score < 0.1


def test_a_high_return_rate_is_elevated() -> None:
    result = score_behavior(replace(BASE, past_orders=10, past_returns=6, recent_returns_30d=2))
    assert result.score >= 0.30
    assert any("Returned 6 of 10" in n for n in result.explanation)


def test_a_new_account_alone_is_not_elevated() -> None:
    """New customers shouldn't be sent to a person just for being new."""
    result = score_behavior(replace(BASE, past_orders=0, past_returns=0, account_age_days=3))
    assert result.score < 0.30


def test_shared_address_raises_risk() -> None:
    shared = score_behavior(replace(BASE, other_accounts_at_address=1)).score
    assert shared > score_behavior(BASE).score


def test_score_never_exceeds_one() -> None:
    worst = BehaviorInputs(50, 50, 20, 0, 10, 10**7, 25000)
    assert score_behavior(worst).score <= 1.0


# --- Governance gate --------------------------------------------------------

CLEAR = GateInputs(
    eligibility=Eligibility.ELIGIBLE,
    photo=PhotoCheck.VERIFIED,
    proposal=Decision.APPROVE,
    ambiguous=False,
    critic_veto=False,
    risk_score=0.05,
    refund_cents=8900,
)
ON = GateSettings(
    automation_enabled=True,
    risk_limit=Decimal("0.30"),
    high_value_limit_cents=25000,
    qa_sample_rate=Decimal("0"),
)


def gate(i: GateInputs = CLEAR, s: GateSettings = ON, draw: float = 0.99) -> GateResult:
    class FixedRng(random.Random):
        def random(self) -> float:
            return draw

    return governance_gate(i, s, rng=FixedRng())


def test_a_clear_case_is_auto_approved() -> None:
    result = gate()
    assert result.route is Route.AUTO_APPROVED
    assert result.evidence_strength is EvidenceStrength.STRONG
    assert result.escalation_reason is None


def test_no_photo_needed_also_counts_as_clear() -> None:
    assert gate(replace(CLEAR, photo=PhotoCheck.NOT_NEEDED)).auto_approved


@pytest.mark.parametrize(
    ("change", "reason", "strength"),
    [
        ({"proposal": Decision.DENY}, EscalationReason.PROPOSED_DENIAL, EvidenceStrength.STRONG),
        (
            {"eligibility": Eligibility.INELIGIBLE},
            EscalationReason.PROPOSED_DENIAL,
            EvidenceStrength.WEAK,
        ),
        ({"ambiguous": True}, EscalationReason.AMBIGUOUS_CALL, EvidenceStrength.MIXED),
        (
            {"eligibility": Eligibility.UNCLEAR},
            EscalationReason.AMBIGUOUS_CALL,
            EvidenceStrength.MIXED,
        ),
        (
            {"photo": PhotoCheck.NOT_VERIFIED},
            EscalationReason.UNVERIFIED_PHOTO,
            EvidenceStrength.WEAK,
        ),
        ({"critic_veto": True}, EscalationReason.CRITIC_CONCERN, EvidenceStrength.MIXED),
        ({"refund_cents": 32900}, EscalationReason.HIGH_VALUE, EvidenceStrength.STRONG),
        ({"risk_score": 0.30}, EscalationReason.ELEVATED_RISK, EvidenceStrength.STRONG),
        ({"proposal": Decision.ESCALATE}, EscalationReason.AMBIGUOUS_CALL, EvidenceStrength.STRONG),
        ({"pipeline_error": True}, EscalationReason.PIPELINE_ERROR, EvidenceStrength.WEAK),
    ],
)
def test_every_named_reason_sends_the_case_to_a_person(
    change: dict[str, object], reason: EscalationReason, strength: EvidenceStrength
) -> None:
    result = gate(replace(CLEAR, **change))  # type: ignore[arg-type]
    assert result.route is Route.REVIEWER
    assert result.escalation_reason is reason
    assert result.evidence_strength is strength


def test_the_ai_can_never_deny_even_with_automation_on_and_everything_else_clear() -> None:
    result = gate(replace(CLEAR, proposal=Decision.DENY), ON)
    assert result.route is Route.REVIEWER
    assert result.escalation_reason is EscalationReason.PROPOSED_DENIAL


def test_an_approve_label_cannot_carry_a_failed_check() -> None:
    """The gate decides from the checks, not from the model's label."""
    result = gate(replace(CLEAR, photo=PhotoCheck.NOT_VERIFIED, proposal=Decision.APPROVE))
    assert not result.auto_approved


def test_automation_off_sends_everything_to_a_person() -> None:
    off = replace(ON, automation_enabled=False)
    result = gate(CLEAR, off)
    assert result.route is Route.REVIEWER
    assert result.escalation_reason is EscalationReason.AUTOMATION_OFF


def test_specific_reasons_outrank_automation_off() -> None:
    off = replace(ON, automation_enabled=False)
    result = gate(replace(CLEAR, ambiguous=True), off)
    assert result.escalation_reason is EscalationReason.AMBIGUOUS_CALL
    assert EscalationReason.AUTOMATION_OFF in result.reasons


def test_reason_priority_order() -> None:
    everything = replace(
        CLEAR,
        pipeline_error=True,
        proposal=Decision.DENY,
        ambiguous=True,
        photo=PhotoCheck.NOT_VERIFIED,
        critic_veto=True,
        refund_cents=99999,
        risk_score=0.9,
    )
    result = gate(everything, replace(ON, automation_enabled=False))
    assert result.reasons == [
        EscalationReason.PIPELINE_ERROR,
        EscalationReason.PROPOSED_DENIAL,
        EscalationReason.AMBIGUOUS_CALL,
        EscalationReason.UNVERIFIED_PHOTO,
        EscalationReason.CRITIC_CONCERN,
        EscalationReason.HIGH_VALUE,
        EscalationReason.ELEVATED_RISK,
        EscalationReason.AUTOMATION_OFF,
    ]


def test_qa_sampling_sends_some_clear_cases_to_a_person() -> None:
    sampled = replace(ON, qa_sample_rate=Decimal("0.10"))
    assert gate(CLEAR, sampled, draw=0.05).escalation_reason is EscalationReason.QA_SAMPLE
    assert gate(CLEAR, sampled, draw=0.50).auto_approved


def test_qa_sampling_never_applies_to_cases_already_escalated() -> None:
    sampled = replace(ON, qa_sample_rate=Decimal("1.0"))
    result = gate(replace(CLEAR, refund_cents=99999), sampled, draw=0.0)
    assert result.reasons == [EscalationReason.HIGH_VALUE]
