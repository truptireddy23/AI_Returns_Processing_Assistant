"""Small helpers for creating test data inside a test's transaction."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import addresses, security
from returnguard.models import Order, OrderItem, Product, ProductCategory, Role, User

PASSWORD = "correct horse battery staple"


async def make_user(
    session: AsyncSession,
    role: Role = Role.CUSTOMER,
    *,
    email: str | None = None,
    password: str = PASSWORD,
    is_active: bool = True,
) -> User:
    user = User(
        email=email or f"{role.value}-{uuid.uuid4().hex[:8]}@example.com",
        display_name=f"Test {role.value}",
        role=role,
        password_hash=security.hash_password(password),
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def make_order(session: AsyncSession, customer: User, price_cents: int = 8900) -> Order:
    product = Product(
        sku=f"T-{uuid.uuid4().hex[:8]}",
        name="Test Sneaker",
        description="A shoe for tests.",
        category=ProductCategory.FOOTWEAR,
        price_cents=price_cents,
    )
    order = Order(
        customer_id=customer.id,
        placed_at=datetime.now(UTC) - timedelta(days=12),
        delivered_at=datetime.now(UTC) - timedelta(days=10),
        shipping_name=customer.display_name,
        shipping_line1="1 Test St",
        shipping_city="Testville",
        shipping_postal_code="00000",
        address_fingerprint=addresses.fingerprint("1 Test St", "Testville", "00000"),
        card_last4="4242",
        total_cents=price_cents,
        items=[OrderItem(product=product, quantity=1, unit_price_cents=price_cents)],
    )
    session.add_all([product, order])
    await session.flush()
    return order
