"""Catalog, checkout, and starting a return, through the API."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import (
    AuditLog,
    Job,
    Order,
    Product,
    ProductCategory,
    Return,
    ReturnPhoto,
    ReturnStatus,
    Role,
    User,
)
from returnguard.storage import StorageError, get_storage

from . import images
from .factories import PASSWORD, make_order, make_user

pytestmark = pytest.mark.db

CARD = {"number": "4242 4242 4242 4242", "exp_month": 12, "exp_year": 2035, "cvc": "123"}
SHIPPING = {
    "name": "Test Person",
    "line1": "1 Test St",
    "city": "Testville",
    "postal_code": "00000",
}


async def sign_in(client: httpx.AsyncClient, user: User) -> str:
    res = await client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    token: str = res.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = token
    return token


async def make_product(session: AsyncSession, price: int = 5000, **kw: Any) -> Product:
    product = Product(
        sku=f"T-{uuid.uuid4().hex[:8]}",
        name=kw.get("name", "Test Mug"),
        description="For tests.",
        category=kw.get("category", ProductCategory.HOME),
        price_cents=price,
        is_final_sale=kw.get("is_final_sale", False),
        photo_key="/products/T.png",
    )
    session.add(product)
    await session.flush()
    return product


async def count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


# --- Catalog ----------------------------------------------------------------


async def test_catalog_is_public(db_client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    product = await make_product(db_session, name="Public Mug")

    listing = (await db_client.get("/api/products")).json()
    one = await db_client.get(f"/api/products/{product.id}")

    assert any(p["name"] == "Public Mug" for p in listing)
    assert one.status_code == 200
    assert one.json()["photo_url"] == "/products/T.png"
    assert (await db_client.get(f"/api/products/{uuid.uuid4()}")).status_code == 404


# --- Checkout ---------------------------------------------------------------


async def test_checkout_charges_server_prices_and_keeps_only_last4(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    mug = await make_product(db_session, price=1250)
    await sign_in(db_client, customer)

    res = await db_client.post(
        "/api/orders",
        json={
            # Same product twice: merged into one line with quantity 3.
            "items": [
                {"product_id": str(mug.id), "quantity": 1},
                {"product_id": str(mug.id), "quantity": 2},
            ],
            "shipping": SHIPPING,
            "card": CARD,
        },
    )

    assert res.status_code == 201, res.text
    order = res.json()
    assert order["total_cents"] == 3750
    assert order["card_last4"] == "4242"
    assert order["delivered_at"] is not None  # demo: instant delivery
    assert [(i["quantity"], i["unit_price_cents"]) for i in order["items"]] == [(3, 1250)]
    assert "4242424242424242" not in res.text and "123" not in str(order["items"])
    audit = await db_session.scalar(select(AuditLog).where(AuditLog.action == "order.placed"))
    assert audit is not None and audit.actor_user_id == customer.id


async def test_declined_card_creates_no_order(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    mug = await make_product(db_session)
    await sign_in(db_client, customer)
    before = await count(db_session, Order)

    res = await db_client.post(
        "/api/orders",
        json={
            "items": [{"product_id": str(mug.id), "quantity": 1}],
            "shipping": SHIPPING,
            "card": {**CARD, "number": "4111 1111 1111 1111"},  # real-format, not a test card
        },
    )

    assert res.status_code == 402
    assert "test cards" in res.json()["detail"]
    assert await count(db_session, Order) == before


@pytest.mark.parametrize(
    "items",
    [
        [{"product_id": "UNKNOWN", "quantity": 1}],
        [{"product_id": "MUG", "quantity": 4}, {"product_id": "MUG", "quantity": 4}],  # > 5 total
        [{"product_id": "MUG", "quantity": 0}],
        [],
    ],
)
async def test_checkout_rejects_bad_carts(
    db_client: httpx.AsyncClient, db_session: AsyncSession, items: list[dict[str, Any]]
) -> None:
    customer = await make_user(db_session)
    mug = await make_product(db_session)
    await sign_in(db_client, customer)
    ids = {"MUG": str(mug.id), "UNKNOWN": str(uuid.uuid4())}
    items = [{**i, "product_id": ids[i["product_id"]]} for i in items]

    res = await db_client.post(
        "/api/orders", json={"items": items, "shipping": SHIPPING, "card": CARD}
    )

    assert res.status_code == 422


async def test_checkout_needs_a_customer_and_csrf(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    mug = await make_product(db_session)
    body = {
        "items": [{"product_id": str(mug.id), "quantity": 1}],
        "shipping": SHIPPING,
        "card": CARD,
    }

    assert (await db_client.post("/api/orders", json=body)).status_code == 401

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    assert (await db_client.post("/api/orders", json=body)).status_code == 403

    customer = await make_user(db_session)
    await sign_in(db_client, customer)
    del db_client.headers["X-CSRF-Token"]
    assert (await db_client.post("/api/orders", json=body)).status_code == 403


# --- Returns ----------------------------------------------------------------


async def start_return(
    client: httpx.AsyncClient,
    item_id: object,
    *,
    reason: str = "defective",
    note: str = "The sole is peeling off.",
    photo: bytes | None = None,
    filename: str = "photo.jpg",
) -> httpx.Response:
    files = {"photo": (filename, photo, "image/jpeg")} if photo is not None else None
    return await client.post(
        "/api/returns",
        data={"order_item_id": str(item_id), "reason": reason, "reason_text": note},
        files=files,
    )


async def test_starting_a_return_stores_the_photo_and_queues_review(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer, price_cents=8900)
    await sign_in(db_client, customer)

    res = await start_return(
        db_client, order.items[0].id, photo=images.jpeg(make="Apple", model="iPhone 15")
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "submitted"
    assert body["refund_amount_cents"] == 8900  # computed by the server
    assert body["photo_required"] is True
    assert len(body["photos"]) == 1

    ret = await db_session.get(Return, uuid.UUID(body["id"]))
    assert ret is not None
    job = await db_session.scalar(select(Job).where(Job.return_id == ret.id))
    assert job is not None and job.kind == "review_return" and job.status.value == "queued"
    photo = await db_session.scalar(select(ReturnPhoto).where(ReturnPhoto.return_id == ret.id))
    assert photo is not None
    assert photo.metadata_summary["camera_make"] == "Apple"
    assert photo.storage_key.startswith(f"returns/{ret.id}/")
    assert (await get_storage().get(photo.storage_key))[:2] == b"\xff\xd8"  # a JPEG


async def test_a_return_without_a_photo_is_accepted_for_the_data_check(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    """Missing evidence is handled by the pipeline's data check (M4), not rejected here."""
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    await sign_in(db_client, customer)

    res = await start_return(db_client, order.items[0].id, reason="damaged")

    assert res.status_code == 201
    assert res.json()["photos"] == []
    assert res.json()["photo_required"] is True


async def test_bad_uploads_are_rejected_and_nothing_is_created(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    await sign_in(db_client, customer)
    before = await count(db_session, Return)

    not_an_image = await start_return(db_client, order.items[0].id, photo=b"MZ\x90\x00 executable")
    bomb = await start_return(
        db_client, order.items[0].id, photo=images.huge_png(), filename="x.png"
    )

    assert not_an_image.status_code == 422
    assert bomb.status_code == 422
    assert await count(db_session, Return) == before


async def test_oversized_uploads_are_refused(
    db_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from returnguard.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_max_bytes", 1000)
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    await sign_in(db_client, customer)

    res = await start_return(db_client, order.items[0].id, photo=images.jpeg(size=(400, 400)))

    assert res.status_code == 413


async def test_storage_outage_fails_cleanly(
    db_client: httpx.AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken_put(*_: object, **__: object) -> None:
        raise StorageError("down")

    monkeypatch.setattr(get_storage(), "put", broken_put)
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    await sign_in(db_client, customer)
    before = await count(db_session, Return)

    res = await start_return(db_client, order.items[0].id, photo=images.jpeg())

    assert res.status_code == 503
    assert await count(db_session, Return) == before


async def test_one_return_per_item_and_only_your_own_items(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    other = await make_user(db_session)
    mine = await make_order(db_session, me)
    theirs = await make_order(db_session, other)
    await sign_in(db_client, me)

    assert (await start_return(db_client, theirs.items[0].id)).status_code == 404
    assert (await start_return(db_client, mine.items[0].id)).status_code == 201
    duplicate = await start_return(db_client, mine.items[0].id)
    assert duplicate.status_code == 409


async def test_undelivered_items_cannot_be_returned(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    order.delivered_at = None
    await db_session.flush()
    await sign_in(db_client, customer)

    assert (await start_return(db_client, order.items[0].id)).status_code == 409


async def test_who_can_see_a_return_and_its_photo(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    order = await make_order(db_session, owner)
    await sign_in(db_client, owner)
    created = (await start_return(db_client, order.items[0].id, photo=images.jpeg())).json()
    photo_url = created["photos"][0]["url"]
    return_url = f"/api/returns/{created['id']}"

    own = await db_client.get(photo_url)
    assert own.status_code == 200
    assert own.headers["content-type"] == "image/jpeg"
    assert own.headers["cache-control"] == "private, no-store"
    assert (await db_client.get(return_url)).status_code == 200

    stranger = await make_user(db_session)
    await sign_in(db_client, stranger)
    assert (await db_client.get(return_url)).status_code == 404
    assert (await db_client.get(photo_url)).status_code == 404

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    assert (await db_client.get(return_url)).status_code == 200
    assert (await db_client.get(photo_url)).status_code == 200

    db_client.cookies.clear()
    assert (await db_client.get(photo_url)).status_code == 401


async def test_customers_see_a_failed_review_as_under_review(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)
    await sign_in(db_client, customer)
    created = (await start_return(db_client, order.items[0].id)).json()
    ret = await db_session.get(Return, uuid.UUID(created["id"]))
    assert ret is not None
    ret.status = ReturnStatus.FAILED
    await db_session.flush()

    mine = (await db_client.get(f"/api/returns/{ret.id}")).json()
    orders = (await db_client.get("/api/orders")).json()

    assert mine["status"] == "under_review"
    assert orders[0]["items"][0]["return_status"] == "under_review"
    assert orders[0]["items"][0]["return_id"] == str(ret.id)

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    assert (await db_client.get(f"/api/returns/{ret.id}")).json()["status"] == "failed"


# --- Order details ------------------------------------------------------------

BILLING = {"name": "Pat Payer", "line1": "9 Billing Rd", "city": "Payville", "postal_code": "11111"}


async def place_order(client: httpx.AsyncClient, product: Product, **extra: Any) -> dict[str, Any]:
    res = await client.post(
        "/api/orders",
        json={
            "items": [{"product_id": str(product.id), "quantity": 2}],
            "shipping": SHIPPING,
            "card": CARD,
            **extra,
        },
    )
    assert res.status_code == 201, res.text
    order: dict[str, Any] = res.json()
    return order


async def test_order_details_show_people_addresses_card_and_times(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    mug = await make_product(db_session, price=1250)
    await sign_in(db_client, customer)
    order = await place_order(db_client, mug, billing=BILLING)

    res = await db_client.get(f"/api/orders/{order['id']}")

    assert res.status_code == 200, res.text
    d = res.json()
    assert d["order_number"] == order["order_number"]
    assert d["customer_name"] == customer.display_name
    assert d["customer_email"] == customer.email
    assert d["shipping"] == SHIPPING
    assert d["billing"] == {**BILLING, "same_as_shipping": False}
    assert d["card_last4"] == "4242"
    assert d["placed_at"] and d["delivered_at"]
    assert d["items_total_cents"] == d["total_cents"] == 2500
    assert d["items"][0]["return_id"] is None  # returnable from the page


async def test_billing_defaults_to_the_shipping_address(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    mug = await make_product(db_session)
    await sign_in(db_client, customer)
    order = await place_order(db_client, mug)

    d = (await db_client.get(f"/api/orders/{order['id']}")).json()

    assert d["billing"] == {**SHIPPING, "same_as_shipping": True}


async def test_orders_from_before_billing_was_collected_show_shipping(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    customer = await make_user(db_session)
    order = await make_order(db_session, customer)  # no billing columns set
    await sign_in(db_client, customer)

    d = (await db_client.get(f"/api/orders/{order.id}")).json()

    assert d["billing"]["same_as_shipping"] is True
    assert d["billing"]["line1"] == order.shipping_line1


async def test_only_the_owner_can_see_an_order(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    owner = await make_user(db_session)
    order = await make_order(db_session, owner)

    stranger = await make_user(db_session)
    await sign_in(db_client, stranger)
    assert (await db_client.get(f"/api/orders/{order.id}")).status_code == 404
    assert (await db_client.get(f"/api/orders/{uuid.uuid4()}")).status_code == 404

    reviewer = await make_user(db_session, Role.REVIEWER)
    await sign_in(db_client, reviewer)
    assert (await db_client.get(f"/api/orders/{order.id}")).status_code == 403

    db_client.cookies.clear()
    assert (await db_client.get(f"/api/orders/{order.id}")).status_code == 401
