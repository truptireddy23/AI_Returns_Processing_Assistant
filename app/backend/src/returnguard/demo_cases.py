"""Load the six ready-made demo cases (app/seed/demo_cases.json).

For each case: a customer with a backdated account, an order history, and past
returns decided by the seeded reviewers; then a recent order and a return submitted
*now*, with its photo stored and validated exactly like a real upload. The return
is queued for the worker, so the real pipeline (data check, policy, photo, behaviour,
recommendation, critic, gate) reviews it.

    python -m returnguard.demo_cases            # load every case not loaded yet
    python -m returnguard.demo_cases --list     # show the cases and their status

Additive and idempotent: a case whose customer already exists is skipped, so it is
safe on a database that has the regular seed (and on the shared Neon database).
The audit log is append-only, so loaded cases can't be deleted afterwards.
Refuses to run when ENVIRONMENT=production.
"""

import argparse
import asyncio
import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import addresses, audit, db, security
from returnguard.config import get_settings
from returnguard.images import process_upload
from returnguard.jobs import REVIEW_JOB
from returnguard.log_config import configure_logging
from returnguard.models import (
    ActorType,
    DeciderType,
    Decision,
    Job,
    MessageSender,
    Order,
    OrderItem,
    PolicyDoc,
    Product,
    ProductPhoto,
    Return,
    ReturnMessage,
    ReturnPhoto,
    ReturnReason,
    ReturnStatus,
    Role,
    User,
)
from returnguard.storage import get_storage
from returnguard.wake import nudge_worker

log = structlog.get_logger(__name__)

CASES_FILE = "demo_cases.json"
PHOTO_DIR = "demo_photos"
HISTORY_REASONS = [ReturnReason.DEFECTIVE, ReturnReason.DAMAGED, ReturnReason.CHANGED_MIND]


@dataclass
class Loaded:
    key: str
    email: str
    case_number: int | None = None
    skipped: bool = False
    notes: list[str] = field(default_factory=list)


def _load_cases(seed_dir: Path) -> list[dict[str, Any]]:
    data: dict[str, Any] = json.loads((seed_dir / CASES_FILE).read_text())
    cases: list[dict[str, Any]] = data["cases"]
    return cases


async def _photo_bytes(session: AsyncSession, seed_dir: Path, spec: str) -> bytes:
    """A file in demo_photos/, or `catalog:<SKU>` for that product's own catalog photo."""
    if spec.startswith("catalog:"):
        sku = spec.split(":", 1)[1]
        photo = await session.scalar(
            select(ProductPhoto)
            .join(Product, Product.id == ProductPhoto.product_id)
            .where(Product.sku == sku)
            .order_by(ProductPhoto.position)
            .limit(1)
        )
        if photo is None:
            raise SystemExit(f"{sku} has no catalog photo to reuse")
        return await get_storage(get_settings().product_photo_bucket).get(photo.storage_key)
    return (seed_dir / PHOTO_DIR / spec).read_bytes()


async def load_case(
    session: AsyncSession, seed_dir: Path, case: dict[str, Any], *, now: datetime
) -> Loaded:
    result = Loaded(key=case["key"], email=case["email"])
    if await session.scalar(select(User.id).where(func.lower(User.email) == case["email"].lower())):
        result.skipped = True
        return result

    rng = random.Random(case["key"])  # noqa: S311  (demo data, not security)
    passwords = json.loads((seed_dir / "users.json").read_text())["passwords"]
    reviewers = list(
        await session.scalars(select(User).where(User.role == Role.REVIEWER).order_by(User.email))
    )
    if not reviewers:
        raise SystemExit("No reviewers found: load the regular seed first (make seed)")
    policy = await session.scalar(select(PolicyDoc).where(PolicyDoc.is_active))
    products = {p.sku: p for p in await session.scalars(select(Product))}
    returnable = sorted(sku for sku, p in products.items() if not p.is_final_sale)

    age = int(case["account_age_days"])
    user = User(
        email=case["email"],
        display_name=case["display_name"],
        role=Role.CUSTOMER,
        password_hash=security.hash_password(passwords["customer"]),
        created_at=now - timedelta(days=age),
    )
    session.add(user)
    await session.flush()

    addr = case["address"]
    fingerprint = addresses.fingerprint(addr["line1"], addr["city"], addr["postal_code"])

    def order(skus: list[str], delivered_at: datetime, quantity: int = 1) -> Order:
        # `quantity` applies to the first item (the one a demo return is about).
        items = [
            OrderItem(
                product=products[s],
                quantity=quantity if i == 0 else 1,
                unit_price_cents=products[s].price_cents,
            )
            for i, s in enumerate(skus)
        ]
        o = Order(
            customer_id=user.id,
            placed_at=delivered_at - timedelta(days=rng.randint(2, 5)),
            delivered_at=delivered_at,
            shipping_name=user.display_name,
            shipping_line1=addr["line1"],
            shipping_city=addr["city"],
            shipping_postal_code=addr["postal_code"],
            address_fingerprint=fingerprint,
            card_last4=case["card_last4"],
            total_cents=sum(i.unit_price_cents * i.quantity for i in items),
            items=items,
        )
        session.add(o)
        return o

    # Order history. Returned orders flagged "recent" were delivered in the last month.
    h = case["history"]
    n_returns = h["approved_returns"] + h["denied_returns"]
    if n_returns > h["orders"]:
        raise SystemExit(f"{case['key']}: more returns than orders")
    history: list[Order] = []
    # Past orders fall inside the account's lifetime: older than the 30-day window
    # when the account is old enough, otherwise spread over its few days.
    # Orders are placed up to 5 days before delivery, hence the 6-day margin.
    newest, oldest = (35, age - 6) if age > 45 else (1, max(age - 6, 1))
    for _ in range(h["orders"]):
        delivered = now - timedelta(days=rng.randint(newest, oldest))
        history.append(order(rng.sample(returnable, k=rng.choice([1, 1, 2])), delivered))
    await session.flush()

    returned = rng.sample(history, k=n_returns)
    outcomes = [Decision.APPROVE] * h["approved_returns"] + [Decision.DENY] * h["denied_returns"]
    rng.shuffle(outcomes)
    for i, (decision, past) in enumerate(zip(outcomes, returned, strict=True)):
        if i < h["recent_returns"]:
            cap = min(24, max(age - 6, 1))
            past.delivered_at = now - timedelta(days=rng.randint(min(8, cap), cap))
            past.placed_at = past.delivered_at - timedelta(days=min(3, age - 1))
        assert past.delivered_at is not None
        created = past.delivered_at + timedelta(days=rng.randint(1, 4))
        item = past.items[0]
        session.add(
            Return(
                order_item_id=item.id,
                customer_id=user.id,
                reason=rng.choice(HISTORY_REASONS),
                refund_amount_cents=item.unit_price_cents,
                status=ReturnStatus.APPROVED
                if decision is Decision.APPROVE
                else ReturnStatus.DENIED,
                final_decision=decision,
                decided_by_type=DeciderType.PERSON,
                decided_by_user_id=rng.choice(reviewers).id,
                decided_at=created + timedelta(days=1),
                policy_version=policy.version if policy else None,
                created_at=created,
            )
        )

    # The return being demonstrated: a recent order, returned now.
    r = case["return"]
    current = order(
        [r["sku"], *r.get("also_in_order", [])],
        now - timedelta(days=int(r["delivered_days_ago"])),
        quantity=int(r.get("quantity", 1)),
    )
    await session.flush()
    item = current.items[0]
    ret = Return(
        id=uuid.uuid4(),
        order_item_id=item.id,
        customer_id=user.id,
        reason=ReturnReason(r["reason"]),
        reason_text=r["note"],
        refund_amount_cents=item.unit_price_cents * item.quantity,  # as the API computes it
        status=ReturnStatus.SUBMITTED,
    )
    session.add(ret)
    await session.flush()

    if r.get("photo"):
        settings = get_settings()
        processed = process_upload(
            await _photo_bytes(session, seed_dir, r["photo"]),
            max_pixels=settings.upload_max_pixels,
            max_side=settings.upload_max_side,
        )
        key = f"returns/{ret.id}/{uuid.uuid4()}.jpg"
        await get_storage().put(key, processed.data, processed.content_type)
        session.add(
            ReturnPhoto(
                return_id=ret.id,
                storage_key=key,
                content_type=processed.content_type,
                size_bytes=len(processed.data),
                sha256=processed.sha256,
                perceptual_hash=processed.perceptual_hash,
                metadata_summary={
                    **processed.metadata,
                    "width": processed.width,
                    "height": processed.height,
                },
            )
        )
        result.notes.append(f"photo {r['photo']}")

    for message in case.get("chat", []):
        sender = MessageSender(message["sender"])
        session.add(
            ReturnMessage(
                return_id=ret.id,
                sender=sender,
                sender_user_id=user.id if sender is MessageSender.CUSTOMER else None,
                body=message["body"],
            )
        )
    if case.get("chat"):
        result.notes.append(f"{len(case['chat'])} chat message(s)")

    session.add(Job(kind=REVIEW_JOB, return_id=ret.id))
    audit.record(
        session,
        actor_type=ActorType.CUSTOMER,
        actor_user_id=user.id,
        action="return.submitted",
        return_id=ret.id,
        details={
            "reason": ret.reason.value,
            "refund_amount_cents": ret.refund_amount_cents,
            "photo": bool(r.get("photo")),
            "demo_case": case["key"],
        },
    )
    await session.flush()
    result.case_number = ret.case_number
    result.notes.append(
        f"{h['orders']} past orders, {n_returns} past returns ({h['recent_returns']} recent)"
    )
    return result


async def load_all(seed_dir: Path, only: set[str] | None = None) -> list[Loaded]:
    if get_settings().environment == "production":
        raise SystemExit("Refusing to load demo cases in production")
    out = []
    now = datetime.now(UTC)
    async for session in db.get_session():
        for case in _load_cases(seed_dir):
            if only and case["key"] not in only:
                continue
            loaded = await load_case(session, seed_dir, case, now=now)
            await session.commit()  # one case at a time, so a failure keeps the others
            out.append(loaded)
            log.info(
                "demo_cases.skipped" if loaded.skipped else "demo_cases.loaded",
                case=loaded.key,
                email=loaded.email,
                case_number=loaded.case_number,
            )
    await nudge_worker()  # the worker reviews the new returns now
    return out


async def list_cases(seed_dir: Path) -> None:
    async for session in db.get_session():
        for case in _load_cases(seed_dir):
            user = await session.scalar(
                select(User).where(func.lower(User.email) == case["email"].lower())
            )
            row = None
            if user:
                row = await session.scalar(
                    select(Return)
                    .where(
                        Return.customer_id == user.id, Return.reason_text == case["return"]["note"]
                    )
                    .order_by(Return.created_at.desc())
                )
            status = f"R-{row.case_number} {row.status.value}" if row else "not loaded"
            print(f"{case['key']:<12} {case['email']:<28} {status:<24} {case['story']}")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true", help="show the cases and their status")
    parser.add_argument("--only", nargs="*", help="load only these case keys")
    args = parser.parse_args()
    seed_dir = Path(settings.seed_dir).resolve()

    async def run() -> None:
        if args.list:
            await list_cases(seed_dir)
        else:
            for c in await load_all(seed_dir, set(args.only) if args.only else None):
                state = "already loaded" if c.skipped else f"R-{c.case_number} submitted"
                print(f"{c.key:<12} {c.email:<28} {state}  {'; '.join(c.notes)}")
        await db.dispose_engine()

    asyncio.run(run())


if __name__ == "__main__":
    main()
