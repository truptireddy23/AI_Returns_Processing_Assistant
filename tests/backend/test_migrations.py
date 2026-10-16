import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from returnguard import db

ALEMBIC_INI = Path(__file__).parents[2] / "app" / "backend" / "alembic.ini"


@pytest.mark.db
@pytest.mark.usefixtures("database")
async def test_migrations_upgrade_to_head_and_enable_pgvector() -> None:
    # Alembic's env.py runs its own event loop, so call it from a worker thread.
    await asyncio.to_thread(command.upgrade, Config(str(ALEMBIC_INI)), "head")

    async with db.get_engine().connect() as conn:
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        has_vector = (
            await conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        ).scalar()
    assert version == "0001"
    assert has_vector == 1
