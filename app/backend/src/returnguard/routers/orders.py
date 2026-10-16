"""Customer: their own orders."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from returnguard.auth import DbSession, require_role
from returnguard.models import Order, OrderItem, ProductCategory, Role, User

router = APIRouter(prefix="/api/orders", tags=["orders"])

Customer = Annotated[User, Depends(require_role(Role.CUSTOMER))]


class OrderItemOut(BaseModel):
    id: str
    product_name: str
    category: ProductCategory
    quantity: int
    unit_price_cents: int
    is_final_sale: bool


class OrderOut(BaseModel):
    id: str
    order_number: int
    placed_at: datetime
    delivered_at: datetime | None
    total_cents: int
    card_last4: str
    items: list[OrderItemOut]


@router.get("", response_model=list[OrderOut])
async def list_my_orders(user: Customer, db: DbSession) -> list[OrderOut]:
    orders = await db.scalars(
        select(Order)
        .where(Order.customer_id == user.id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.placed_at.desc())
    )
    return [
        OrderOut(
            id=str(o.id),
            order_number=o.order_number,
            placed_at=o.placed_at,
            delivered_at=o.delivered_at,
            total_cents=o.total_cents,
            card_last4=o.card_last4,
            items=[
                OrderItemOut(
                    id=str(i.id),
                    product_name=i.product.name,
                    category=i.product.category,
                    quantity=i.quantity,
                    unit_price_cents=i.unit_price_cents,
                    is_final_sale=i.product.is_final_sale,
                )
                for i in o.items
            ],
        )
        for o in orders
    ]
