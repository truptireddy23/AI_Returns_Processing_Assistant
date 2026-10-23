"""Step 4, behaviour risk: a transparent, rule-based score (no trained model).

Every factor is listed with its weight, so a reviewer (and the bias audit, M8)
can see exactly why a score is what it is. Only account behaviour is used:
never names, addresses as text, or anything that stands in for a protected
characteristic. Shared shipping addresses are compared by fingerprint.

The score is in [0, 1]; the gate compares it with the admin's risk limit.
"""

from dataclasses import dataclass, field

# Weight of each factor at full strength. They sum to 1.0.
WEIGHTS = {
    "return_rate": 0.40,  # share of past orders that were returned
    "recent_returns": 0.20,  # returns started in the last 30 days
    "new_account": 0.15,  # very new accounts have no track record
    "shared_address": 0.15,  # other accounts ship to the same address
    "refund_size": 0.10,  # large refunds relative to the high-value limit
}


@dataclass(frozen=True)
class BehaviorInputs:
    past_orders: int  # excluding the order being returned
    past_returns: int  # excluding this return
    recent_returns_30d: int  # excluding this return
    account_age_days: int
    other_accounts_at_address: int
    refund_cents: int
    high_value_limit_cents: int


@dataclass(frozen=True)
class BehaviorScore:
    score: float
    factors: dict[str, float] = field(default_factory=dict)  # name -> contribution
    explanation: list[str] = field(default_factory=list)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_behavior(i: BehaviorInputs) -> BehaviorScore:
    strengths: dict[str, float] = {}
    notes: list[str] = []

    if i.past_orders >= 3:
        rate = i.past_returns / i.past_orders
        # 10% returns is normal; 60%+ is the top of the scale.
        strengths["return_rate"] = _clamp((rate - 0.10) / 0.50)
        notes.append(f"Returned {i.past_returns} of {i.past_orders} past orders ({rate:.0%}).")
    else:
        # Too few orders for a rate to mean anything; covered by "new_account".
        strengths["return_rate"] = 0.0
        notes.append(f"Only {i.past_orders} past orders: no meaningful return rate yet.")

    strengths["recent_returns"] = _clamp(i.recent_returns_30d / 3)
    if i.recent_returns_30d:
        notes.append(f"{i.recent_returns_30d} other return(s) in the last 30 days.")

    if i.account_age_days < 30:
        strengths["new_account"] = _clamp(1 - i.account_age_days / 30)
        notes.append(f"Account is {i.account_age_days} day(s) old.")
    else:
        strengths["new_account"] = 0.0

    strengths["shared_address"] = _clamp(i.other_accounts_at_address / 2)
    if i.other_accounts_at_address:
        notes.append(f"{i.other_accounts_at_address} other account(s) ship to the same address.")

    strengths["refund_size"] = _clamp(i.refund_cents / max(1, i.high_value_limit_cents))

    contributions = {name: round(WEIGHTS[name] * s, 4) for name, s in strengths.items()}
    return BehaviorScore(
        score=round(sum(contributions.values()), 4),
        factors=contributions,
        explanation=notes,
    )
