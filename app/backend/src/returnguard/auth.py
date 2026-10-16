"""Login sessions, CSRF protection, and role checks.

- The browser holds an opaque random token in an httpOnly, SameSite=Lax cookie;
  the database stores only its SHA-256 hash.
- Every state-changing request from a signed-in user must echo the session's
  CSRF token in the X-CSRF-Token header.
- Roles are checked server-side on every endpoint via `require_role`.
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from returnguard import audit, security
from returnguard.config import get_settings
from returnguard.db import get_session
from returnguard.models import Role, Session, User
from returnguard.ratelimit import FailureLimit, rate_limit

log = structlog.get_logger(__name__)

SESSION_COOKIE = "rg_session"
CSRF_HEADER = "X-CSRF-Token"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

DbSession = Annotated[AsyncSession, Depends(get_session)]


# --- Schemas ----------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: Role


class AuthState(BaseModel):
    user: UserOut
    csrf_token: str


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id), email=user.email, display_name=user.display_name, role=user.role
    )


# --- Dependencies -----------------------------------------------------------


async def current_session(request: Request, db: DbSession) -> Session:
    """The signed-in user's session, enforcing CSRF on state-changing requests."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    session = await db.get(Session, security.hash_token(token))
    if session is None or session.expires_at <= datetime.now(UTC) or not session.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")

    if request.method not in _SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not security.tokens_match(sent, session.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token")

    structlog.contextvars.bind_contextvars(user_id=str(session.user_id))
    return session


CurrentSession = Annotated[Session, Depends(current_session)]


def require_role(*roles: Role) -> Callable[[Session], Awaitable[User]]:
    """Dependency: the signed-in user, who must hold one of `roles`."""

    async def dependency(session: CurrentSession) -> User:
        if session.user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
        return session.user

    return dependency


# --- Routes -----------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Failed sign-ins per account, so guessing one account's password is throttled
# even if the attacker rotates IP addresses.
_account_failures = FailureLimit(get_settings().login_account_failure_limit, "login-account")


@router.post(
    "/login",
    response_model=AuthState,
    dependencies=[Depends(rate_limit(get_settings().login_rate_limit, "login"))],
)
async def login(
    body: LoginRequest, request: Request, response: Response, db: DbSession
) -> AuthState:
    settings = get_settings()
    account_key = body.email.lower()
    await _account_failures.check(account_key)
    user = await db.scalar(select(User).where(func.lower(User.email) == account_key))

    password_ok = security.verify_password(user.password_hash if user else None, body.password)
    if user is None or not password_ok or not user.is_active:
        await _account_failures.record_failure(account_key)
        log.info("auth.login_failed", known_user=user is not None)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    # Drop this user's expired sessions while we're here.
    await db.execute(
        delete(Session).where(Session.user_id == user.id, Session.expires_at <= func.now())
    )

    token = security.new_token()
    session = Session(
        token_hash=security.hash_token(token),
        user_id=user.id,
        csrf_token=security.new_token(),
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours),
        user_agent=(request.headers.get("user-agent") or "")[:255] or None,
    )
    db.add(session)
    audit.record(
        db,
        actor_type=audit.actor_for_role(user.role),
        actor_user_id=user.id,
        action="auth.login",
    )
    await db.commit()

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    log.info("auth.login", user_id=str(user.id), role=user.role.value)
    return AuthState(user=_user_out(user), csrf_token=session.csrf_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(session: CurrentSession, response: Response, db: DbSession) -> None:
    audit.record(
        db,
        actor_type=audit.actor_for_role(session.user.role),
        actor_user_id=session.user_id,
        action="auth.logout",
    )
    await db.delete(session)
    await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=AuthState)
async def me(session: CurrentSession) -> AuthState:
    return AuthState(user=_user_out(session.user), csrf_token=session.csrf_token)
