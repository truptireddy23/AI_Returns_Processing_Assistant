"""Code-only checks (no model calls).

- Step 1, the **data check** (M6): is the request complete? Missing evidence goes
  back to the customer; it is never a reason to decide.
- The **policy facts** that are arithmetic, not judgment: the return window
  (P1), Final Sale (P6), and the high-value limit (P7). The policy step (M6)
  receives these as results; models never do date or threshold maths.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from returnguard.models import ReturnReason

# Reasons that need a photo under policy P4.
PHOTO_REASONS = frozenset(
    {
        ReturnReason.DAMAGED,
        ReturnReason.DEFECTIVE,
        ReturnReason.WRONG_ITEM,
        ReturnReason.NOT_AS_DESCRIBED,
    }
)
# Reasons that still allow a Final Sale item back (P6).
FINAL_SALE_EXCEPTIONS = frozenset(
    {ReturnReason.DAMAGED, ReturnReason.DEFECTIVE, ReturnReason.WRONG_ITEM}
)
RETURN_WINDOW_DAYS = 30
# Day counting uses the shop's calendar, so "day 30" doesn't depend on UTC midnight.
SHOP_TIMEZONE = ZoneInfo("America/Chicago")


@dataclass(frozen=True)
class DataCheck:
    complete: bool
    missing: list[str] = field(default_factory=list)
    customer_message: str | None = None


def data_check(*, reason: ReturnReason, photo_count: int, delivered: bool) -> DataCheck:
    missing = []
    if reason in PHOTO_REASONS and photo_count == 0:
        missing.append("photo")
    if not delivered:
        missing.append("delivery")
    if not missing:
        return DataCheck(complete=True)
    message = (
        "We need a photo of the problem to continue."
        if missing == ["photo"]
        else "We can't review this return yet: the item hasn't been delivered."
    )
    return DataCheck(complete=False, missing=missing, customer_message=message)


def shop_date(moment: datetime) -> date:
    return moment.astimezone(SHOP_TIMEZONE).date()


def days_since_delivery(delivered_at: datetime, requested_at: datetime) -> int:
    """Delivery day is day 0 (P1)."""
    return (shop_date(requested_at) - shop_date(delivered_at)).days


@dataclass(frozen=True)
class PolicyFacts:
    days_since_delivery: int
    within_window: bool  # P1
    final_sale_blocks: bool  # P6: Final Sale and not one of the allowed reasons
    high_value: bool  # P7: refund above the high-value limit
    photo_required: bool  # P4

    def blocking_clauses(self) -> list[str]:
        """Clauses that make the return ineligible on the facts alone."""
        clauses = []
        if not self.within_window:
            clauses.append("P1")
        if self.final_sale_blocks:
            clauses.append("P6")
        return clauses


def policy_facts(
    *,
    reason: ReturnReason,
    delivered_at: datetime,
    requested_at: datetime,
    is_final_sale: bool,
    refund_cents: int,
    high_value_limit_cents: int,
) -> PolicyFacts:
    days = days_since_delivery(delivered_at, requested_at)
    return PolicyFacts(
        days_since_delivery=days,
        within_window=0 <= days <= RETURN_WINDOW_DAYS,
        final_sale_blocks=is_final_sale and reason not in FINAL_SALE_EXCEPTIONS,
        high_value=refund_cents > high_value_limit_cents,
        photo_required=reason in PHOTO_REASONS,
    )
