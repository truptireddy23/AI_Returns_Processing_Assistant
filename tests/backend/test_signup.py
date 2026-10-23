"""Customers can create their own accounts; nobody can create a staff account."""

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import security
from returnguard.auth import SESSION_COOKIE
from returnguard.models import AuditLog, Role, User

from .factories import make_user

pytestmark = pytest.mark.db

GOOD = {
    "email": "new.shopper@example.com",
    "password": "violet-kettle-42",
    "display_name": "New Shopper",
}


async def signup(client: httpx.AsyncClient, **overrides: object) -> httpx.Response:
    return await client.post("/api/auth/signup", json={**GOOD, **overrides})


async def test_signup_creates_a_customer_and_signs_them_in(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    res = await signup(db_client)

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["user"]["role"] == "customer"
    assert body["user"]["display_name"] == "New Shopper"
    assert body["csrf_token"]
    assert "HttpOnly" in res.headers["set-cookie"] and res.cookies[SESSION_COOKIE]

    me = await db_client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["user"]["email"] == GOOD["email"]
    # The new customer can use customer endpoints straight away.
    assert (await db_client.get("/api/orders")).json() == []

    user = await db_session.scalar(select(User).where(User.email == GOOD["email"]))
    assert user is not None
    assert user.password_hash != GOOD["password"]
    assert security.verify_password(user.password_hash, GOOD["password"])
    actions = (
        await db_session.scalars(select(AuditLog.action).where(AuditLog.actor_user_id == user.id))
    ).all()
    assert actions == ["auth.signup", "auth.login"]


@pytest.mark.parametrize("role", ["admin", "reviewer", "customer"])
async def test_signup_refuses_any_role_field(db_client: httpx.AsyncClient, role: str) -> None:
    res = await signup(db_client, role=role)
    assert res.status_code == 422


async def test_new_accounts_cannot_reach_staff_endpoints(db_client: httpx.AsyncClient) -> None:
    await signup(db_client)
    assert (await db_client.get("/api/review/queue")).status_code == 403
    assert (await db_client.get("/api/admin/settings")).status_code == 403


async def test_email_must_be_unique_ignoring_case(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await make_user(db_session, email="Taken@Example.com")

    res = await signup(db_client, email="taken@example.com")

    assert res.status_code == 409
    assert res.json()["detail"] == "An account with this email already exists"
    assert SESSION_COOKIE not in res.cookies
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(func.lower(User.email) == "taken@example.com")
    )
    assert count == 1


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("short1", "at least 10"),
        ("password123", "too common"),
        ("new.shopper", "can't be your email"),  # the email's name part
        ("new.shopper@example.com", "can't be your email"),
        ("aaaaaaaaaaaa", "mix of characters"),
        ("abababababab", "mix of characters"),
    ],
)
async def test_weak_passwords_are_refused(
    db_client: httpx.AsyncClient, password: str, message: str
) -> None:
    res = await signup(db_client, password=password)
    assert res.status_code == 422
    assert message in res.json()["detail"]


@pytest.mark.parametrize(
    "overrides",
    [{"email": "not-an-email"}, {"display_name": ""}, {"display_name": "x" * 101}],
)
async def test_malformed_signups_are_refused(
    db_client: httpx.AsyncClient, overrides: dict[str, str]
) -> None:
    assert (await signup(db_client, **overrides)).status_code == 422


async def test_signup_is_rate_limited_per_client(db_client: httpx.AsyncClient) -> None:
    statuses = [
        (await signup(db_client, email=f"shopper{i}@example.com")).status_code for i in range(6)
    ]
    assert statuses == [201] * 5 + [429]


async def test_a_new_account_can_sign_in_again(db_client: httpx.AsyncClient) -> None:
    csrf = (await signup(db_client)).json()["csrf_token"]
    await db_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    res = await db_client.post(
        "/api/auth/login", json={"email": GOOD["email"].upper(), "password": GOOD["password"]}
    )
    assert res.status_code == 200
    assert res.json()["user"]["role"] == Role.CUSTOMER.value
