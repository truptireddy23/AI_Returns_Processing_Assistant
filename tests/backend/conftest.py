"""Shared fixtures for backend tests.

Database tests run against a separate `<name>_test` database (created and
migrated once per session), and each test runs inside a transaction that is
rolled back afterwards — so tests never see each other's data or your dev data.

Locally, database tests are skipped when Postgres is down; in CI
(`REQUIRE_DB=1`) they fail instead, so a missing database can't pass silently.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from returnguard.config import get_settings

# --- Point the app at the test database before anything reads settings. ------
_base_url = make_url(
    os.environ.get("DATABASE_URL") or get_settings().database_url.get_secret_value()
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _base_url.set(
    database=f"{_base_url.database}_test"
).render_as_string(hide_password=False)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("ENVIRONMENT", "test")
get_settings.cache_clear()

from returnguard import db, ratelimit  # noqa: E402  (must follow the env setup above)
from returnguard.main import create_app  # noqa: E402

REPO_ROOT = Path(__file__).parents[2]
ALEMBIC_INI = REPO_ROOT / "app" / "backend" / "alembic.ini"
SEED_DIR = REPO_ROOT / "app" / "seed"


async def _ensure_test_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


def _migrate() -> None:
    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(ALEMBIC_INI)), "head")


@pytest.fixture(scope="session")
async def migrated_db() -> AsyncIterator[None]:
    try:
        await _ensure_test_database()
    except Exception as exc:
        if os.environ.get("REQUIRE_DB") == "1":
            pytest.fail(f"Database required but unreachable: {exc!r}")
        pytest.skip("Postgres not reachable (run `make up`)")
    # Alembic's env.py runs its own event loop, so call it from a worker thread.
    await asyncio.to_thread(_migrate)
    yield
    await db.dispose_engine()


@pytest.fixture
async def db_session(migrated_db: None) -> AsyncIterator[AsyncSession]:
    """A session whose work is rolled back after the test (commits become savepoints)."""
    async with db.get_engine().connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture(autouse=True)
async def _reset_rate_limits() -> AsyncIterator[None]:
    await ratelimit.reset()
    yield


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """An API client that doesn't need the database."""
    transport = httpx.ASGITransport(app=create_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_client(db_session: AsyncSession) -> AsyncIterator[httpx.AsyncClient]:
    """An API client whose requests share the test's rolled-back transaction."""
    app = create_app()

    async def _session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[db.get_session] = _session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
