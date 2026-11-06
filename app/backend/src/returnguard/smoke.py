"""HTTP smoke check. --live creates synthetic data and uses the configured provider.

Run only against a private local database. Never use --live against shared demo data.
"""

import argparse
import json
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx


def checked(response: httpx.Response) -> Any:
    response.raise_for_status()
    return response.json()


def run(
    base_url: str, *, live: bool = False, expect_failure: bool = False, timeout: int = 300
) -> None:
    if live and urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Live smoke is restricted to a private loopback deployment")
    with httpx.Client(base_url=base_url, timeout=35) as client:
        for route in ("/api/healthz", "/api/readyz", "/api/products"):
            checked(client.get(route))
            print(json.dumps({"check": route, "status": "passed"}), flush=True)
        if not live:
            return
        products = checked(client.get("/api/products"))
        product = next(p for p in products if not p["is_final_sale"] and p["price_cents"] < 25000)
        account = checked(
            client.post(
                "/api/auth/signup",
                json={
                    "email": f"cp3-smoke-{secrets.token_hex(6)}@example.com",
                    "password": "Smoke-" + secrets.token_urlsafe(24),
                    "display_name": "Synthetic Smoke",
                },
            )
        )
        headers = {"X-CSRF-Token": account["csrf_token"]}
        order = checked(
            client.post(
                "/api/orders",
                headers=headers,
                json={
                    "items": [{"product_id": product["id"], "quantity": 1}],
                    "shipping": {
                        "name": "Synthetic Smoke",
                        "line1": "123 Demo Street",
                        "city": "Example City",
                        "postal_code": "60000",
                    },
                    "card": {
                        "number": "4242424242424242",
                        "exp_month": 12,
                        "exp_year": datetime.now(UTC).year + 2,
                        "cvc": "123",
                    },
                },
            )
        )
        item_id = order["items"][0]["id"]
        ret = checked(
            client.post(
                "/api/returns",
                headers=headers,
                data={
                    "order_item_id": item_id,
                    "reason": "changed_mind",
                    "reason_text": "Synthetic Smoke says she changed plans. synthetic@example.com.",
                },
            )
        )
        return_id = ret["id"]
        deadline = time.monotonic() + timeout
        while ret["status"] in {"submitted", "checking"} and time.monotonic() < deadline:
            time.sleep(2)
            ret = checked(client.get(f"/api/returns/{return_id}"))
        if ret["status"] in {"submitted", "checking"}:
            raise RuntimeError("Pipeline did not finish within smoke timeout")
        # A second item exercises missing evidence without an inference call.
        order2 = checked(
            client.post(
                "/api/orders",
                headers=headers,
                json={
                    "items": [{"product_id": product["id"], "quantity": 1}],
                    "shipping": {
                        "name": "Synthetic Smoke",
                        "line1": "123 Demo Street",
                        "city": "Example City",
                        "postal_code": "60000",
                    },
                    "card": {
                        "number": "4242424242424242",
                        "exp_month": 12,
                        "exp_year": datetime.now(UTC).year + 2,
                        "cvc": "123",
                    },
                },
            )
        )
        missing = checked(
            client.post(
                "/api/returns",
                headers=headers,
                data={
                    "order_item_id": order2["items"][0]["id"],
                    "reason": "damaged",
                    "reason_text": "Synthetic missing photo test.",
                },
            )
        )
        while missing["status"] in {"submitted", "checking"} and time.monotonic() < deadline:
            time.sleep(1)
            missing = checked(client.get(f"/api/returns/{missing['id']}"))
        if missing["status"] != "needs_info":
            raise RuntimeError("Missing photo did not route to needs_info")
    seed = json.loads((Path(__file__).resolve().parents[3] / "seed/users.json").read_text())
    with httpx.Client(base_url=base_url, timeout=35) as reviewer:
        checked(
            reviewer.post(
                "/api/auth/login",
                json={
                    "email": "riley.chen@example.com",
                    "password": seed["passwords"]["reviewer"],
                },
            )
        )
        case = checked(reviewer.get(f"/api/review/cases/{return_id}"))
        if expect_failure:
            if case["escalation_reason"] != "pipeline_error" or case["final_decision"] is not None:
                raise RuntimeError("Provider failure did not fail closed into human review")
        elif case["ai"]["source"] != "model":
            raise RuntimeError(
                f"Model recommendation missing: source={case['ai']['source']}, "
                f"escalation={case['escalation_reason']}"
            )
        trace = reviewer.get(f"/api/review/cases/{return_id}/events")
        trace.raise_for_status()
        if not expect_failure and not all(
            name in trace.text for name in ("search_policy", "check_return_window")
        ):
            raise RuntimeError("The two policy function calls are missing from the trace")
        print(
            json.dumps(
                {
                    "check": "live_pipeline",
                    "status": "passed",
                    "return_id": return_id,
                    "outcome": case["status"],
                    "source": case["ai"]["source"],
                    "recovery": expect_failure,
                    "missing_evidence": "needs_info",
                    "sse": trace.headers.get("content-type"),
                }
            ),
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--expect-failure", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if args.expect_failure and not args.live:
        parser.error("--expect-failure requires --live")
    run(args.base_url, live=args.live, expect_failure=args.expect_failure, timeout=args.timeout)


if __name__ == "__main__":
    main()
