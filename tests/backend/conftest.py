"""Shared fixtures for backend tests.

Tests marked `db` need a reachable Postgres at DATABASE_URL. Locally they are
skipped when the database is down; in CI (`REQUIRE_DB=1`) they fail instead, so a
missing database can never pass silently.
"""

import os
from collections.abc import AsyncIterator

import httpx
import pytest

from returnguard import db
from returnguard.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db.dispose_engine()


@pytest.fixture
async def database() -> AsyncIterator[None]:
    try:
        await db.ping()
    except Exception as exc:
        await db.dispose_engine()
        if os.environ.get("REQUIRE_DB") == "1":
            pytest.fail(f"Database required but unreachable: {exc!r}")
        pytest.skip("Postgres not reachable at DATABASE_URL (run `make up`)")
    yield
    await db.dispose_engine()
