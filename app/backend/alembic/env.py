"""Alembic environment: reads the database URL from ReturnGuard settings."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import NullPool
from sqlalchemy.engine import Connection

from returnguard import db, models  # noqa: F401  (models registers every table)
from returnguard.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Migrations always use a direct connection, never a transaction pooler.
database_url = db.direct_database_url()


def run_migrations_offline() -> None:
    context.configure(
        url=database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = db.create_engine(database_url, poolclass=NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
