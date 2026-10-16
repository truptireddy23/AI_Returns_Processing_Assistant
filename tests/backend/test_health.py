import httpx
import pytest

from returnguard import __version__, db


async def test_healthz_reports_ok_without_database(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "version": __version__}


async def test_responses_carry_a_request_id(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/healthz", headers={"X-Request-ID": "a" * 32})
    assert res.headers["X-Request-ID"] == "a" * 32

    res = await client.get("/api/healthz")
    assert res.headers.get("X-Request-ID")


async def test_readyz_returns_503_when_database_is_down(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_ping() -> None:
        raise ConnectionRefusedError

    monkeypatch.setattr(db, "ping", failing_ping)
    res = await client.get("/api/readyz")
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable", "database": "unreachable"}


@pytest.mark.db
@pytest.mark.usefixtures("migrated_db")
async def test_readyz_ok_with_database(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/readyz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}
