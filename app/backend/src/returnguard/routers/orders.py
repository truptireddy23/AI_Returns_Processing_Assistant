"""Customer: checkout and their own orders."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard import addresses, audit
from returnguard.auth import DbSession, require_role
from returnguard.config import get_settings
from returnguard.models import (
    ActorType,
    Order,
    OrderItem,
    Product,
    ProductCategory,
    Return,
    ReturnStatus,
    Role,
    User,
)
from returnguard.payments import PaymentDeclined, charge_test_card
from returnguard.ratelimit import rate_limit
from returnguard.routers.returns import customer_status

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/orders", tags=["orders"])

Customer = Annotated[User, Depends(require_role(Role.CUSTOMER))]

MAX_QUANTITY = 5


# --- Schemas ----------------------------------------------------------------


class OrderItemOut(BaseModel):
    id: str
    product_id: str
    product_name: str
    category: ProductCategory
    photo_url: str | None
    quantity: int
    unit_price_cents: int
    is_final_sale: bool
    return_id: str | None
    return_status: ReturnStatus | None


class OrderOut(BaseModel):
    id: str
    order_number: int
    placed_at: datetime
    delivered_at: datetime | None
    total_cents: int
    card_last4: str
    items: list[OrderItemOut]


class CartLine(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(ge=1, le=MAX_QUANTITY)


class ShippingAddress(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    line1: str = Field(min_length=1, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)


class TestCard(BaseModel):
    number: SecretStr  # never logged or echoed back
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2000, le=2100)
    cvc: SecretStr


class CheckoutRequest(BaseModel):
    items: list[CartLine] = Field(min_length=1, max_length=20)
    shipping: ShippingAddress
    card: TestCard


# --- Helpers ----------------------------------------------------------------


async def _order_out(db: DbSession, orders: list[Order]) -> list[OrderOut]:
    item_ids = [i.id for o in orders for i in o.items]
    returns = {
        r.order_item_id: r
        for r in await db.scalars(select(Return).where(Return.order_item_id.in_(item_ids)))
    }
    out = []
    for o in orders:
        items = []
        for i in o.items:
            ret = returns.get(i.id)
            items.append(
                OrderItemOut(
                    id=str(i.id),
                    product_id=str(i.product_id),
                    product_name=i.product.name,
                    category=i.product.category,
                    photo_url=i.product.photo_key,
                    quantity=i.quantity,
                    unit_price_cents=i.unit_price_cents,
                    is_final_sale=i.product.is_final_sale,
                    return_id=str(ret.id) if ret else None,
                    return_status=customer_status(ret.status) if ret else None,
                )
            )
        out.append(
            OrderOut(
                id=str(o.id),
                order_number=o.order_number,
                placed_at=o.placed_at,
                delivered_at=o.delivered_at,
                total_cents=o.total_cents,
                card_last4=o.card_last4,
                items=items,
            )
        )
    return out


# --- Routes -----------------------------------------------------------------


@router.get("", response_model=list[OrderOut])
async def list_my_orders(user: Customer, db: DbSession) -> list[OrderOut]:
    orders = await db.scalars(
        select(Order)
        .where(Order.customer_id == user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.placed_at.desc())
    )
    return await _order_out(db, list(orders))


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(get_settings().checkout_rate_limit, "checkout"))],
)
async def checkout(body: CheckoutRequest, user: Customer, db: DbSession) -> OrderOut:
    # Merge repeated products and look up real prices; never trust the browser's.
    quantities: dict[uuid.UUID, int] = {}
    for line in body.items:
        quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity
    if any(q > MAX_QUANTITY for q in quantities.values()):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"At most {MAX_QUANTITY} of each item"
        )
    products = {
        p.id: p for p in await db.scalars(select(Product).where(Product.id.in_(quantities)))
    }
    if missing := set(quantities) - set(products):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unknown product: {sorted(map(str, missing))[0]}",
        )

    try:
        last4 = charge_test_card(
            body.card.number.get_secret_value(),
            body.card.exp_month,
            body.card.exp_year,
            body.card.cvc.get_secret_value(),
        )
    except PaymentDeclined as exc:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, str(exc)) from exc

    now = datetime.now(UTC)
    ship = body.shipping
    items = [
        OrderItem(product_id=pid, quantity=qty, unit_price_cents=products[pid].price_cents)
        for pid, qty in quantities.items()
    ]
    order = Order(
        customer_id=user.id,
        placed_at=now,
        # Demo shop: delivery is instant, so a return can be started right away.
        delivered_at=now,
        shipping_name=ship.name,
        shipping_line1=ship.line1,
        shipping_city=ship.city,
        shipping_postal_code=ship.postal_code,
        address_fingerprint=addresses.fingerprint(ship.line1, ship.city, ship.postal_code),
        card_last4=last4,
        total_cents=sum(i.unit_price_cents * i.quantity for i in items),
        items=items,
    )
    db.add(order)
    await db.flush()
    audit.record(
        db,
        actor_type=ActorType.CUSTOMER,
        actor_user_id=user.id,
        action="order.placed",
        details={"order_number": order.order_number, "total_cents": order.total_cents},
    )
    await db.commit()
    log.info("order.placed", order_number=order.order_number, items=len(items))

    fresh = await db.scalar(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .execution_options(populate_existing=True)
    )
    assert fresh is not None
    return (await _order_out(db, [fresh]))[0]
