"""The CP4 benchmark scorer: metrics are computed exactly as the report defines them."""

import os
from typing import Any

from returnguard.benchmark import is_quota_error
from returnguard.benchmark_report import (
    mcnemar_exact,
    percentile,
    score_variant,
    slept,
    wilson,
)


def case(key: str, route: str, proposal: list[str], photo: str | None = None) -> dict[str, Any]:
    return {
        "key": key,
        "category": "c",
        "expected": {"route": route, "proposal": proposal, "photo": photo},
    }


def row(
    key: str,
    route: str,
    proposal: str | None,
    *,
    check: str | None = None,
    tokens: int = 0,
    decided: tuple[str | None, str | None] = (None, None),
    repeat: int = 1,
) -> dict[str, Any]:
    steps: dict[str, Any] = {"policy": {"latency_ms": 1000, "tokens_in": tokens, "tokens_out": 0}}
    if check:
        steps["image"] = {"check": check, "latency_ms": 2000, "tokens_in": tokens, "tokens_out": 0}
    return {
        "case": key,
        "category": "c",
        "repeat": repeat,
        "route": route,
        "ai_proposal": proposal,
        "final_decision": decided[0],
        "decided_by_type": decided[1],
        "wall_ms": 1500,
        "steps": steps,
        "error": None,
    }


CASES = {
    "ok-auto": case("ok-auto", "auto_approved", ["approve"]),
    "worn": case("worn", "reviewer", ["deny", "escalate"]),
    "late": case("late", "reviewer", ["deny"]),
    "nophoto": case("nophoto", "customer", []),
    "photo": case("photo", "reviewer", ["escalate"], photo="not_verified"),
}


def test_unsafe_auto_approvals_and_route_accuracy() -> None:
    rows = [
        row("ok-auto", "auto_approved", "approve"),
        row("worn", "auto_approved", "approve"),  # unsafe: should have gone to a person
        row("late", "reviewer", "deny"),
        row("nophoto", "customer", None),
        row("photo", "reviewer", "escalate", check="not_verified"),
    ]
    s = score_variant(CASES, rows, None)
    assert s["route_accuracy"] == 80.0
    assert s["unsafe_auto_approvals"] == ["worn"]
    assert s["missed_automations"] == []
    assert s["automatic_denials"] == 0
    assert s["needs_person"] == {
        "precision": 1.0,
        "recall": 0.75,
        "f1": 0.857,
        "tp": 3,
        "fp": 0,
        "fn": 1,
    }
    assert s["proposal_acceptable"] == 75.0  # "worn" proposed approve
    assert s["photo_accuracy"] == 100.0
    assert s["confusion"]["reviewer"]["auto_approved"] == 1


def test_missed_automation_and_automatic_denial_are_counted() -> None:
    rows = [
        row("ok-auto", "reviewer", "approve"),
        row("late", "reviewer", "deny", decided=("deny", "auto")),
    ]
    s = score_variant(CASES, rows, None)
    assert s["missed_automations"] == ["ok-auto"]
    assert s["automatic_denials"] == 1


def test_tokens_cost_and_repeat_consistency() -> None:
    rows = [
        row("late", "reviewer", "deny", tokens=1000),
        row("late", "reviewer", "deny", tokens=1000, repeat=2),
        row("worn", "reviewer", "deny", tokens=3000),
        row("worn", "auto_approved", "approve", tokens=3000, repeat=2),
    ]
    s = score_variant(CASES, rows, (1.0, 2.0))
    assert s["cases"] == 2  # repeat 1 only for accuracy
    assert s["tokens"]["in"] == 1000 + 3000  # first repeat only; one policy step each
    assert s["cost_usd"] == round(4000 / 1e6, 4)
    assert s["repeats"] == {"cases_with_repeats": 2, "route_consistent": 1}


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([], 0.5) is None


def test_quota_and_key_errors_stop_the_run() -> None:
    class RateLimitError(Exception):
        pass

    assert is_quota_error(RateLimitError("Error code: 429"))
    assert is_quota_error(Exception("Error code: 401 - Invalid API Key"))
    assert not is_quota_error(ValueError("bad JSON from the model"))


def test_wilson_and_exact_mcnemar() -> None:
    assert wilson(30, 32) == [79.9, 98.3]
    assert wilson(0, 0) is None
    assert mcnemar_exact(2, 3) == 1.0
    assert mcnemar_exact(0, 6) == 0.0312
    assert mcnemar_exact(0, 0) == 1.0


def test_cases_that_span_a_sleep_are_left_out_of_latency() -> None:
    awake = row("late", "reviewer", "deny", tokens=1000)
    asleep = row("worn", "reviewer", "deny", tokens=1000)
    asleep["steps"]["policy"]["latency_ms"] = 600_000  # wall clock kept running
    assert not slept(awake) and slept(asleep)
    s = score_variant(CASES, [awake, asleep], None)
    assert s["latency_cases"] == 1
    assert s["latency_excluded_sleep"] == ["worn"]
    assert s["cases"] == 2  # the outcome still counts


def test_importing_the_runner_does_not_redirect_the_database() -> None:
    assert "returnguard_bench" not in os.environ["DATABASE_URL"]
