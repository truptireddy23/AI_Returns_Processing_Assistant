"""Every role can reach its own endpoints and is refused everyone else's."""

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard.models import Role

from .factories import PASSWORD, make_order, make_user

pytestmark = pytest.mark.db

ENDPOINTS = {
    "orders": "/api/orders",
    "queue": "/api/review/queue",
    "settings": "/api/admin/settings",
}

# Which endpoints each role may use. Admins hold every reviewer right.
ALLOWED = {
    Role.CUSTOMER: {"orders"},
    Role.REVIEWER: {"queue"},
    Role.ADMIN: {"queue", "settings"},
}


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("endpoint", list(ENDPOINTS))
async def test_role_access_matrix(
    db_client: httpx.AsyncClient, db_session: AsyncSession, role: Role, endpoint: str
) -> None:
    user = await make_user(db_session, role)
    await db_client.post("/api/auth/login", json={"email": user.email, "password": PASSWORD})

    res = await db_client.get(ENDPOINTS[endpoint])

    expected = 200 if endpoint in ALLOWED[role] else 403
    assert res.status_code == expected, res.text


@pytest.mark.parametrize("path", list(ENDPOINTS.values()))
async def test_signed_out_requests_are_401(db_client: httpx.AsyncClient, path: str) -> None:
    assert (await db_client.get(path)).status_code == 401


async def test_customers_see_only_their_own_orders(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session)
    other = await make_user(db_session)
    mine = await make_order(db_session, me)
    await make_order(db_session, other)

    await db_client.post("/api/auth/login", json={"email": me.email, "password": PASSWORD})
    orders = (await db_client.get("/api/orders")).json()

    assert [o["id"] for o in orders] == [str(mine.id)]
    assert orders[0]["items"][0]["product_name"] == "Test Sneaker"


async def test_settings_start_with_automation_off(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    admin = await make_user(db_session, Role.ADMIN)
    await db_client.post("/api/auth/login", json={"email": admin.email, "password": PASSWORD})

    body = (await db_client.get("/api/admin/settings")).json()

    assert body["automation_enabled"] is False
    assert body["risk_limit"] == "0.30"
    assert body["high_value_limit_cents"] == 25000
    assert body["qa_sample_rate"] == "0.10"
