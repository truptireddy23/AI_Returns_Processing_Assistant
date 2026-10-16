"""Database engine and session factory (SQLAlchemy 2, async)."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import URL, MetaData, NullPool, make_url, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from returnguard.config import get_settings

# Used when DATABASE_URL is empty: the Postgres container from docker-compose,
# reached from the host.
LOCAL_DATABASE_URL = "postgresql+asyncpg://returnguard:returnguard@localhost:5432/returnguard"

# Deterministic constraint names, so migrations can reference them.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def normalise_url(raw: str) -> URL:
    """Turn any Postgres URL (e.g. one copied from Neon) into an asyncpg URL.

    Hosted providers hand out libpq-style URLs such as
    `postgresql://u:p@host/db?sslmode=require&channel_binding=require`.
    asyncpg spells `sslmode` as `ssl` and doesn't take `channel_binding`
    (it still authenticates with SCRAM), so translate rather than make people
    edit the string by hand.
    """
    url = make_url(raw.strip() or LOCAL_DATABASE_URL)
    if url.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must be a PostgreSQL URL")
    query = dict(url.query)
    if "sslmode" in query and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return url.set(drivername="postgresql+asyncpg", query=query)


def uses_pooler(url: URL) -> bool:
    """True for transaction-mode poolers such as Neon's `-pooler` endpoints."""
    return "-pooler" in (url.host or "")


def engine_options(url: URL) -> dict[str, Any]:
    options: dict[str, Any] = {
        "pool_pre_ping": True,  # a scaled-to-zero database drops idle connections
        "pool_recycle": 300,
    }
    if uses_pooler(url):
        # A transaction pooler hands each transaction to a different server
        # connection, so asyncpg's named prepared statements would collide.
        options = {
            "poolclass": NullPool,
            "connect_args": {
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
                "prepared_statement_cache_size": 0,
                "statement_cache_size": 0,
            },
        }
    return options


def database_url() -> URL:
    """The URL for application traffic (pooled, if the provider offers it)."""
    return normalise_url(get_settings().database_url.get_secret_value())


def direct_database_url() -> URL:
    """A direct connection, for migrations and session state (never a pooler)."""
    settings = get_settings()
    url = normalise_url(
        settings.database_url_unpooled.get_secret_value()
        or settings.database_url.get_secret_value()
    )
    if uses_pooler(url):
        raise ValueError(
            "Migrations need a direct connection: set DATABASE_URL_UNPOOLED "
            "(the connection string without '-pooler' in the host)"
        )
    return url


def create_engine(url: URL | None = None, **overrides: Any) -> AsyncEngine:
    url = url or database_url()
    return create_async_engine(url, **{**engine_options(url), **overrides})


def describe(url: URL) -> dict[str, Any]:
    """Where we're connecting, safe to log (no credentials)."""
    return {"db_host": url.host, "db_name": url.database, "db_pooler": uses_pooler(url)}


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is None:
        _engine = create_engine()
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    get_engine()
    assert _sessionmaker is not None
    async with _sessionmaker() as session:
        yield session


async def ping() -> None:
    """Raise if the database is unreachable."""
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
