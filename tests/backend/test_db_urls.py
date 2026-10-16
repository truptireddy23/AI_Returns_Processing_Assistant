"""Connection strings from hosted providers (Neon) work as pasted."""

import pytest
from pydantic import SecretStr
from sqlalchemy import NullPool

from returnguard import db
from returnguard.config import Settings

NEON_POOLED = (
    "postgresql://neondb_owner:secret@ep-quiet-sun-123456-pooler.c-7.us-east-2.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=require"
)
NEON_DIRECT = NEON_POOLED.replace("-pooler", "")


def test_neon_url_is_translated_for_asyncpg() -> None:
    url = db.normalise_url(NEON_POOLED)
    assert url.drivername == "postgresql+asyncpg"
    assert dict(url.query) == {"ssl": "require"}
    assert url.password == "secret"
    assert url.database == "neondb"


def test_empty_url_means_the_local_docker_database() -> None:
    assert db.normalise_url("  ").render_as_string(hide_password=False) == db.LOCAL_DATABASE_URL


def test_non_postgres_urls_are_rejected() -> None:
    with pytest.raises(ValueError, match="PostgreSQL"):
        db.normalise_url("mysql://u:p@host/db")


def test_pooled_connections_disable_prepared_statement_reuse() -> None:
    pooled = db.engine_options(db.normalise_url(NEON_POOLED))
    assert pooled["poolclass"] is NullPool
    assert pooled["connect_args"]["statement_cache_size"] == 0
    assert pooled["connect_args"]["prepared_statement_name_func"]() != (
        pooled["connect_args"]["prepared_statement_name_func"]()
    )

    direct = db.engine_options(db.normalise_url(NEON_DIRECT))
    assert "poolclass" not in direct
    assert direct["pool_pre_ping"] is True


def test_migrations_use_the_direct_url(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        database_url=SecretStr(NEON_POOLED), database_url_unpooled=SecretStr(NEON_DIRECT)
    )
    monkeypatch.setattr(db, "get_settings", lambda: settings)

    assert db.uses_pooler(db.database_url())
    assert not db.uses_pooler(db.direct_database_url())


def test_migrations_refuse_a_pooled_url(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(database_url=SecretStr(NEON_POOLED), database_url_unpooled=SecretStr(""))
    monkeypatch.setattr(db, "get_settings", lambda: settings)

    with pytest.raises(ValueError, match="DATABASE_URL_UNPOOLED"):
        db.direct_database_url()


def test_describe_never_includes_credentials() -> None:
    described = db.describe(db.normalise_url(NEON_POOLED))
    assert "secret" not in repr(described)
    assert described["db_pooler"] is True
