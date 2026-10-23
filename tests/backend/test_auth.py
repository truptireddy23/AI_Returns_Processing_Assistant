from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import db, ratelimit, security
from returnguard.auth import SESSION_COOKIE
from returnguard.main import create_app
from returnguard.models import AuditLog, Role, Session

from .factories import PASSWORD, make_user

pytestmark = pytest.mark.db


async def login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def test_login_sets_an_httponly_session_cookie(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, Role.REVIEWER)

    res = await login(db_client, user.email)

    assert res.status_code == 200
    body = res.json()
    assert body["user"] == {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": "reviewer",
    }
    assert body["csrf_token"]
    cookie = res.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie


async def test_session_token_is_stored_only_as_a_hash(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    res = await login(db_client, user.email)
    token = res.cookies[SESSION_COOKIE]

    stored = (await db_session.scalars(select(Session).where(Session.user_id == user.id))).one()
    assert stored.token_hash == security.hash_token(token)
    assert stored.token_hash != token


async def test_login_is_case_insensitive_on_email(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, email="Mixed.Case@Example.com")
    assert (await login(db_client, "mixed.case@example.com")).status_code == 200
    assert user.email == "Mixed.Case@Example.com"


@pytest.mark.parametrize("case", ["wrong_password", "unknown_email", "inactive_user"])
async def test_failed_logins_all_look_the_same(
    db_client: httpx.AsyncClient, db_session: AsyncSession, case: str
) -> None:
    user = await make_user(db_session, is_active=case != "inactive_user")
    email = "nobody@example.com" if case == "unknown_email" else user.email
    password = "wrong" if case == "wrong_password" else PASSWORD

    res = await login(db_client, email, password)

    assert res.status_code == 401
    assert res.json() == {"detail": "Invalid email or password"}
    assert SESSION_COOKIE not in res.cookies


async def test_me_returns_the_signed_in_user(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, Role.ADMIN)
    csrf = (await login(db_client, user.email)).json()["csrf_token"]

    res = await db_client.get("/api/auth/me")

    assert res.status_code == 200
    assert res.json()["user"]["role"] == "admin"
    assert res.json()["csrf_token"] == csrf


async def test_me_without_a_session_is_401(db_client: httpx.AsyncClient) -> None:
    res = await db_client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json() == {"detail": "Not signed in"}


async def test_forged_cookie_is_401(db_client: httpx.AsyncClient) -> None:
    db_client.cookies.set(SESSION_COOKIE, "not-a-real-token")
    assert (await db_client.get("/api/auth/me")).status_code == 401


async def test_expired_session_is_401(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    token = security.new_token()
    db_session.add(
        Session(
            token_hash=security.hash_token(token),
            user_id=user.id,
            csrf_token=security.new_token(),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    await db_session.flush()
    db_client.cookies.set(SESSION_COOKIE, token)

    assert (await db_client.get("/api/auth/me")).status_code == 401


async def test_deactivated_user_loses_their_session(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    await login(db_client, user.email)
    user.is_active = False
    await db_session.flush()

    assert (await db_client.get("/api/auth/me")).status_code == 401


async def test_logout_requires_the_csrf_token(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    csrf = (await login(db_client, user.email)).json()["csrf_token"]

    missing = await db_client.post("/api/auth/logout")
    wrong = await db_client.post("/api/auth/logout", headers={"X-CSRF-Token": "nope"})
    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert (await db_client.get("/api/auth/me")).status_code == 200  # still signed in

    res = await db_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert res.status_code == 204


async def test_logout_ends_the_session(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    login_res = await login(db_client, user.email)
    token = login_res.cookies[SESSION_COOKIE]
    csrf = login_res.json()["csrf_token"]

    await db_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    # Replaying the old cookie no longer works.
    db_client.cookies.set(SESSION_COOKIE, token)
    assert (await db_client.get("/api/auth/me")).status_code == 401
    assert await db_session.get(Session, security.hash_token(token)) is None


async def test_login_and_logout_are_audited(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session, Role.REVIEWER)
    csrf = (await login(db_client, user.email)).json()["csrf_token"]
    await db_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})

    entries = (
        await db_session.scalars(
            select(AuditLog).where(AuditLog.actor_user_id == user.id).order_by(AuditLog.id)
        )
    ).all()
    assert [(e.actor_type.value, e.action) for e in entries] == [
        ("reviewer", "auth.login"),
        ("reviewer", "auth.logout"),
    ]


async def test_login_is_rate_limited_per_client(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    statuses = [(await login(db_client, user.email, "wrong")).status_code for _ in range(10)]
    assert statuses == [401] * 10

    blocked = await login(db_client, user.email)  # even the right password
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_login_rejects_malformed_input(db_client: httpx.AsyncClient) -> None:
    res = await db_client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert res.status_code == 422


async def test_failed_logins_are_limited_per_account_across_addresses(
    db_session: AsyncSession,
) -> None:
    """Rotating IP addresses doesn't help guess one account's password."""
    user = await make_user(db_session)
    app = create_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[db.get_session] = _session

    async def attempt(ip: str, password: str = "wrong") -> int:
        transport = httpx.ASGITransport(app=app, client=(ip, 1234))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return (await login(c, user.email, password)).status_code

    # 20 failures, each from a different address (so the per-IP limit never trips).
    assert [await attempt(f"10.0.0.{i}") for i in range(20)] == [401] * 20
    # The account is now locked, even with the right password from a new address.
    assert await attempt("10.0.1.1", PASSWORD) == 429
    # Other accounts are unaffected.
    other = await make_user(db_session)
    transport = httpx.ASGITransport(app=app, client=("10.0.1.2", 1234))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        assert (await login(c, other.email)).status_code == 200


async def test_successful_logins_do_not_count_toward_the_account_limit(
    db_client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    for _ in range(25):
        res = await login(db_client, user.email)
        assert res.status_code in (200, 429)
        if res.status_code == 429:  # the per-IP limit, not the account one
            ratelimit.reset()
    ratelimit.reset()
    assert (await login(db_client, user.email)).status_code == 200
