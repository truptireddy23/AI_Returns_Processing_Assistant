"""Load the synthetic seed data (app/seed/*.json) into an empty database.

Run with `make seed`. Safe to re-run: it does nothing if users already exist.
Refuses to run when ENVIRONMENT=production. Dates are relative to now, so the
demo orders are always inside (or, deliberately, outside) the return window.
"""

import asyncio
import json
import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import addresses, audit, db, security
from returnguard.config import get_settings
from returnguard.log_config import configure_logging
from returnguard.models import (
    ActorType,
    DeciderType,
    Decision,
    Order,
    OrderItem,
    PolicyChunk,
    PolicyDoc,
    Product,
    ProductCategory,
    Return,
    ReturnReason,
    ReturnStatus,
    Role,
    User,
)

log = structlog.get_logger(__name__)

RANDOM_SEED = 492  # history is generated deterministically


@dataclass
class SeedSummary:
    users: int = 0
    products: int = 0
    orders: int = 0
    returns: int = 0
    policy_clauses: int = 0
    skipped: bool = False


def _load(seed_dir: Path, name: str) -> Any:
    return json.loads((seed_dir / name).read_text())


async def seed(session: AsyncSession, seed_dir: Path, now: datetime | None = None) -> SeedSummary:
    """Insert all seed data in the caller's transaction (the caller commits)."""
    settings = get_settings()
    if settings.environment == "production":
        raise RuntimeError("Refusing to seed demo data in production")

    summary = SeedSummary()
    if await session.scalar(select(func.count()).select_from(User)):
        summary.skipped = True
        return summary

    now = now or datetime.now(UTC)
    rng = random.Random(RANDOM_SEED)  # noqa: S311  (demo data, not security)
    users_data = _load(seed_dir, "users.json")
    passwords: dict[str, str] = users_data["passwords"]

    # Staff
    staff: list[User] = []
    for s in users_data["staff"]:
        user = User(
            email=s["email"],
            display_name=s["display_name"],
            role=Role(s["role"]),
            password_hash=security.hash_password(passwords[s["role"]]),
            created_at=now - timedelta(days=800),
        )
        staff.append(user)
    reviewers = [u for u in staff if u.role == Role.REVIEWER]

    # Customers
    customers: dict[str, tuple[User, dict[str, Any]]] = {}
    customer_hash = security.hash_password(passwords["customer"])
    for c in users_data["customers"]:
        user = User(
            email=c["email"],
            display_name=c["display_name"],
            role=Role.CUSTOMER,
            password_hash=customer_hash,
            created_at=now - timedelta(days=c["account_age_days"]),
        )
        customers[c["key"]] = (user, c)
    session.add_all([*staff, *(u for u, _ in customers.values())])
    summary.users = len(staff) + len(customers)

    # Products
    products: dict[str, Product] = {}
    for p in _load(seed_dir, "products.json"):
        products[p["sku"]] = Product(
            sku=p["sku"],
            name=p["name"],
            description=p["description"],
            category=ProductCategory(p["category"]),
            price_cents=p["price_cents"],
            is_final_sale=p.get("is_final_sale", False),
        )
    session.add_all(products.values())
    summary.products = len(products)

    # Policy
    policy = _load(seed_dir, "policy_v1.json")
    doc = PolicyDoc(
        version=policy["version"],
        title=policy["title"],
        effective_date=date.fromisoformat(policy["effective_date"]),
        is_active=True,
    )
    doc.chunks = [
        PolicyChunk(clause_id=c["clause_id"], title=c["title"], body=c["body"])
        for c in policy["clauses"]
    ]
    session.add(doc)
    summary.policy_clauses = len(doc.chunks)

    def make_order(
        customer: User, profile: dict[str, Any], sku_list: list[str], delivered_at: datetime
    ) -> Order:
        addr = profile["address"]
        items = [
            OrderItem(product=products[sku], quantity=1, unit_price_cents=products[sku].price_cents)
            for sku in sku_list
        ]
        order = Order(
            customer_id=customer.id,
            placed_at=delivered_at - timedelta(days=rng.randint(2, 5)),
            delivered_at=delivered_at,
            shipping_name=customer.display_name,
            shipping_line1=addr["line1"],
            shipping_city=addr["city"],
            shipping_postal_code=addr["postal_code"],
            address_fingerprint=addresses.fingerprint(
                addr["line1"], addr["city"], addr["postal_code"]
            ),
            card_last4=profile["card_last4"],
            total_cents=sum(i.unit_price_cents * i.quantity for i in items),
            items=items,
        )
        session.add(order)
        summary.orders += 1
        return order

    await session.flush()  # assign user ids

    # Order and return history, generated per customer profile.
    returnable = [sku for sku, p in products.items() if not p.is_final_sale]
    for user, profile in customers.values():
        n_orders = profile["history_orders"]
        if n_orders == 0:
            continue
        # History orders were all delivered more than 30 days ago.
        span = max(profile["account_age_days"] - 35, n_orders)
        history: list[Order] = []
        for _ in range(n_orders):
            delivered = now - timedelta(days=35 + rng.randint(0, span))
            skus = rng.sample(returnable, k=rng.choice([1, 1, 2]))
            history.append(make_order(user, profile, skus, delivered))
        await session.flush()  # assign order item ids for the returns below

        outcomes = [Decision.APPROVE] * profile["history_returns"]["approved"] + [
            Decision.DENY
        ] * profile["history_returns"]["denied"]
        for decision, order in zip(outcomes, rng.sample(history, k=len(outcomes)), strict=True):
            item = order.items[0]
            assert order.delivered_at is not None
            decided_at = order.delivered_at + timedelta(days=rng.randint(4, 12))
            by_person = decision == Decision.DENY or rng.random() < 0.5
            session.add(
                Return(
                    order_item_id=item.id,
                    customer_id=user.id,
                    reason=rng.choice(
                        [ReturnReason.DEFECTIVE, ReturnReason.DAMAGED, ReturnReason.CHANGED_MIND]
                    ),
                    reason_text="",
                    refund_amount_cents=item.unit_price_cents,
                    status=ReturnStatus.APPROVED
                    if decision == Decision.APPROVE
                    else ReturnStatus.DENIED,
                    final_decision=decision,
                    decided_by_type=DeciderType.PERSON if by_person else DeciderType.AUTO,
                    decided_by_user_id=rng.choice(reviewers).id if by_person else None,
                    decided_at=decided_at,
                    policy_version=policy["version"],
                    created_at=decided_at - timedelta(days=2),
                )
            )
            summary.returns += 1

    # Demo orders: recent, each set up for one live-demo case.
    for d in _load(seed_dir, "demo_orders.json")["orders"]:
        user, profile = customers[d["customer"]]
        make_order(user, profile, [d["sku"]], now - timedelta(days=d["delivered_days_ago"]))

    audit.record(
        session,
        actor_type=ActorType.SYSTEM,
        action="seed.loaded",
        details={
            "users": summary.users,
            "products": summary.products,
            "orders": summary.orders,
            "returns": summary.returns,
            "policy_version": policy["version"],
        },
    )
    await session.flush()
    return summary


async def _main(seed_dir: Path) -> None:
    async for session in db.get_session():
        summary = await seed(session, seed_dir)
        if summary.skipped:
            log.info("seed.skipped", reason="database already has users")
        else:
            await session.commit()
            log.info("seed.loaded", **vars(summary))
    await db.dispose_engine()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    asyncio.run(_main(Path(settings.seed_dir).resolve()))


if __name__ == "__main__":
    main()
