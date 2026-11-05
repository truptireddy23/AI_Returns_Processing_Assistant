"""Step 7, the governance gate: the only place a review becomes a decision.

A pure function of the check results and the admin's settings, so every rule
can be tested exhaustively. It decides from the *checks*, not from the model's
label: a recommendation of "approve" can't carry a case past a failed check.

Fixed rules (no setting changes them):
- The AI never denies. A proposed denial always goes to a person (M1).
- An unverified photo is never auto-approved (M5).
- An ambiguous call always goes to a person (M4).
- A pipeline failure always goes to a person (fail closed).
"""

import random
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from returnguard.models import Decision, EscalationReason, EvidenceStrength, Route


class PhotoCheck(StrEnum):
    NOT_NEEDED = "not_needed"  # the reason doesn't need a photo
    VERIFIED = "verified"  # matches the product and looks genuine
    NOT_VERIFIED = "not_verified"  # anything else: mismatch, suspicious, or not checked


class Eligibility(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCLEAR = "unclear"


@dataclass(frozen=True)
class GateInputs:
    eligibility: Eligibility
    photo: PhotoCheck
    proposal: Decision  # the recommendation step's proposal
    ambiguous: bool
    critic_veto: bool
    risk_score: float
    refund_cents: int
    pipeline_error: bool = False


@dataclass(frozen=True)
class GateSettings:
    automation_enabled: bool
    risk_limit: Decimal
    high_value_limit_cents: int
    qa_sample_rate: Decimal


@dataclass(frozen=True)
class GateResult:
    route: Route
    evidence_strength: EvidenceStrength
    escalation_reason: EscalationReason | None = None
    # Every reason that applied, in priority order; the first is the one shown.
    reasons: list[EscalationReason] = field(default_factory=list)

    @property
    def auto_approved(self) -> bool:
        return self.route is Route.AUTO_APPROVED


def evidence_strength(i: GateInputs) -> EvidenceStrength:
    """Strong: every check clear. Mixed: warnings. Weak: a check failed (M3)."""
    if (
        i.pipeline_error
        or i.eligibility is Eligibility.INELIGIBLE
        or i.photo is PhotoCheck.NOT_VERIFIED
    ):
        return EvidenceStrength.WEAK
    if i.eligibility is Eligibility.UNCLEAR or i.ambiguous or i.critic_veto:
        return EvidenceStrength.MIXED
    return EvidenceStrength.STRONG


def governance_gate(
    i: GateInputs, s: GateSettings, *, rng: random.Random | None = None
) -> GateResult:
    strength = evidence_strength(i)
    reasons: list[EscalationReason] = []

    # In priority order (BUILD_PLAN.md section 5); the first one is shown.
    if i.pipeline_error:
        reasons.append(EscalationReason.PIPELINE_ERROR)
    if i.proposal is Decision.DENY or i.eligibility is Eligibility.INELIGIBLE:
        reasons.append(EscalationReason.PROPOSED_DENIAL)
    if i.ambiguous or i.eligibility is Eligibility.UNCLEAR:
        reasons.append(EscalationReason.AMBIGUOUS_CALL)
    if i.photo is PhotoCheck.NOT_VERIFIED:
        reasons.append(EscalationReason.UNVERIFIED_PHOTO)
    if i.critic_veto:
        reasons.append(EscalationReason.CRITIC_CONCERN)
    if i.refund_cents > s.high_value_limit_cents:
        reasons.append(EscalationReason.HIGH_VALUE)
    if Decimal(str(i.risk_score)) >= s.risk_limit:
        reasons.append(EscalationReason.ELEVATED_RISK)
    if i.proposal is not Decision.APPROVE and not reasons:
        # The AI asked for a person without a named reason: treat it as ambiguous.
        reasons.append(EscalationReason.AMBIGUOUS_CALL)
    if not s.automation_enabled:
        reasons.append(EscalationReason.AUTOMATION_OFF)

    if not reasons and strength is not EvidenceStrength.STRONG:
        reasons.append(EscalationReason.AMBIGUOUS_CALL)  # belt and braces

    if not reasons:
        # Everything is clear: QA-sample a share of would-be auto-approvals (C2).
        draw = (rng or random.SystemRandom()).random()
        if Decimal(str(draw)) < s.qa_sample_rate:
            reasons.append(EscalationReason.QA_SAMPLE)

    if reasons:
        return GateResult(
            route=Route.REVIEWER,
            evidence_strength=strength,
            escalation_reason=reasons[0],
            reasons=reasons,
        )
    return GateResult(route=Route.AUTO_APPROVED, evidence_strength=strength)
