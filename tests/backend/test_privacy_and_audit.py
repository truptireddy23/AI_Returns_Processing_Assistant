"""Privacy boundaries and fairness screening failures, without real customer data."""

from dataclasses import asdict
from decimal import Decimal

import pytest
from pydantic import ValidationError

from returnguard.bias_audit import audit_rows
from returnguard.config import Settings
from returnguard.pipeline.behavior import BehaviorInputs
from returnguard.pipeline.llm import OpenAIClient
from returnguard.pipeline.privacy import sanitize_text


def test_contact_details_and_gender_are_removed_without_losing_evidence() -> None:
    note = (
        "She is Jordan Ellis. Email jordan@example.com, +1 (312) 555-0100, "
        "123 Main Street. Sole split on day 4."
    )
    masked = sanitize_text(note, ("Jordan Ellis", "Jordan", "Ellis"))
    for private in ("Jordan", "Ellis", "jordan@example.com", "312", "123 Main", "She"):
        assert private not in masked
    assert "Sole split on day 4" in masked


def test_identifiers_use_word_boundaries_and_unicode_normalization() -> None:
    assert sanitize_text("\uff21\uff4c\uff49\uff43\uff45 has a defective shoe", ("Alice",)) == (
        "[identity] has a defective shoe"
    )
    assert sanitize_text("The seam detached", ("He",)) == "The seam detached"


def row(group: str, *, high_risk: bool = False) -> dict[str, str]:
    inputs = BehaviorInputs(10, 9 if high_risk else 1, 3 if high_risk else 0, 365, 0, 1000, 25000)
    return {"group": group, **{k: str(v) for k, v in asdict(inputs).items()}}


def test_matched_groups_have_identical_risk_and_screen_detects_shift() -> None:
    matched = audit_rows([row("a"), row("b")], reference="a")
    assert not matched["flagged"]
    assert matched["groups"]["b"]["pass_rate_ratio"] == 1
    assert matched["groups"]["b"]["small_sample"]
    shifted = audit_rows([row("a"), row("b", high_risk=True)], reference="a")
    assert shifted["flagged"]
    assert shifted["groups"]["b"]["pass_rate_ratio"] == 0


def test_zero_reference_rate_is_undefined_and_bad_data_is_refused() -> None:
    report = audit_rows([row("a", high_risk=True), row("b")], reference="a")
    assert report["groups"]["b"]["pass_rate_ratio"] is None
    with pytest.raises(ValueError, match="reference"):
        audit_rows([row("b")], reference="a")
    with pytest.raises(ValueError, match="nonnegative"):
        audit_rows([{**row("a"), "account_age_days": "-1"}, row("b")], reference="a")


def test_cost_is_decimal_estimate_and_unknown_price_stays_unknown() -> None:
    client = OpenAIClient(
        input_usd_per_million=Decimal("0.2"), output_usd_per_million=Decimal("0.6")
    )
    assert client.estimate_cost(1000, 500) == Decimal("0.0005")
    assert OpenAIClient().estimate_cost(1000, 500) is None
    with pytest.raises(ValidationError):
        Settings(_env_file=None, chat_input_usd_per_million=Decimal("-1"))
