"""The pipeline's judgment steps, behind one interface so M5/M6 can swap in models.

`RuleSteps` is the stand-in used until the model client exists. It is honest
about what it can't do: it never claims to have checked a photo, so any return
that needs one goes to a person as "unverified photo". Its outputs are marked
`"source": "rules"` in the trace.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from returnguard.models import Decision, ReturnReason
from returnguard.pipeline.behavior import BehaviorScore
from returnguard.pipeline.checks import PolicyFacts
from returnguard.pipeline.gate import Eligibility, PhotoCheck

# The clauses that normally support an eligible return, by reason.
SUPPORTING_CLAUSES = {
    ReturnReason.DAMAGED: ["P2", "P4"],
    ReturnReason.DEFECTIVE: ["P2", "P4"],
    ReturnReason.WRONG_ITEM: ["P8", "P4"],
    ReturnReason.NOT_AS_DESCRIBED: ["P8", "P4"],
    ReturnReason.CHANGED_MIND: ["P5"],
}


@dataclass(frozen=True)
class Case:
    """What the judgment steps may see. Names, emails, and addresses are not here (M8)."""

    reason: ReturnReason
    reason_text: str  # customer text: data, never instructions
    product_name: str
    product_category: str
    is_final_sale: bool
    refund_cents: int
    photo_keys: list[str]
    policy_version: int


@dataclass(frozen=True)
class PolicyResult:
    eligibility: Eligibility
    cited_clauses: list[str]
    reason: str
    source: str
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhotoResult:
    check: PhotoCheck
    notes: list[str]
    source: str
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Recommendation:
    proposal: Decision
    rationale: str
    uncertain_about: list[str]
    ambiguous: bool
    source: str
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CriticResult:
    veto: bool
    concern: str | None
    source: str
    output: dict[str, Any] = field(default_factory=dict)


class Steps(Protocol):
    async def policy(self, case: Case, facts: PolicyFacts) -> PolicyResult: ...
    async def photo(self, case: Case, facts: PolicyFacts) -> PhotoResult: ...
    async def recommend(
        self,
        case: Case,
        facts: PolicyFacts,
        policy: PolicyResult,
        photo: PhotoResult,
        behavior: BehaviorScore,
    ) -> Recommendation: ...
    async def critic(
        self,
        case: Case,
        policy: PolicyResult,
        photo: PhotoResult,
        recommendation: Recommendation,
    ) -> CriticResult: ...


class RuleSteps:
    """Deterministic stand-ins for the AI steps (replaced in M5/M6)."""

    source = "rules"

    async def policy(self, case: Case, facts: PolicyFacts) -> PolicyResult:
        blocking = facts.blocking_clauses()
        if blocking:
            why = []
            if "P1" in blocking:
                why.append(f"requested on day {facts.days_since_delivery}, after the 30-day window")
            if "P6" in blocking:
                why.append(
                    "the item was Final Sale and the reason isn't damage, defect, or wrong item"
                )
            return PolicyResult(
                eligibility=Eligibility.INELIGIBLE,
                cited_clauses=blocking,
                reason="Not eligible: " + "; ".join(why) + ".",
                source=self.source,
            )
        clauses = ["P1", *SUPPORTING_CLAUSES[case.reason]]
        return PolicyResult(
            eligibility=Eligibility.ELIGIBLE,
            cited_clauses=clauses,
            reason=f"Within the return window (day {facts.days_since_delivery} of 30).",
            source=self.source,
        )

    async def photo(self, case: Case, facts: PolicyFacts) -> PhotoResult:
        if not facts.photo_required:
            return PhotoResult(
                PhotoCheck.NOT_NEEDED, ["No photo needed for this reason."], self.source
            )
        return PhotoResult(
            PhotoCheck.NOT_VERIFIED,
            ["Photo received but not yet checked: the photo check arrives with the AI steps."],
            self.source,
        )

    async def recommend(
        self,
        case: Case,
        facts: PolicyFacts,
        policy: PolicyResult,
        photo: PhotoResult,
        behavior: BehaviorScore,
    ) -> Recommendation:
        if policy.eligibility is Eligibility.INELIGIBLE:
            return Recommendation(
                Decision.DENY, policy.reason, [], ambiguous=False, source=self.source
            )
        if photo.check is PhotoCheck.NOT_VERIFIED:
            return Recommendation(
                Decision.ESCALATE,
                "Eligible on the policy facts, but the photo hasn't been checked.",
                ["Whether the photo shows the claimed problem"],
                ambiguous=False,
                source=self.source,
            )
        return Recommendation(
            Decision.APPROVE,
            policy.reason,
            [],
            ambiguous=False,
            source=self.source,
        )

    async def critic(
        self,
        case: Case,
        policy: PolicyResult,
        photo: PhotoResult,
        recommendation: Recommendation,
    ) -> CriticResult:
        return CriticResult(veto=False, concern=None, source=self.source)
