from collections.abc import Iterator

import httpx
import pytest
from fastapi import Request

from returnguard import __version__, db, ratelimit, worker
from returnguard.config import get_settings


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


@pytest.fixture
def hosted(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Settings as on Vercel: proxy secret and cron secret set."""
    monkeypatch.setenv("API_PROXY_SECRET", "proxy-secret")
    monkeypatch.setenv("CRON_SECRET", "cron-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.usefixtures("hosted")
async def test_hosted_api_only_answers_the_proxy(client: httpx.AsyncClient) -> None:
    assert (await client.get("/api/readyz")).status_code == 404
    wrong = {"x-proxy-secret": "guess"}
    assert (await client.get("/api/readyz", headers=wrong)).status_code == 404
    assert (await client.get("/api/healthz")).status_code == 200  # platform health checks


@pytest.mark.usefixtures("hosted")
async def test_sweep_needs_the_cron_secret(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def no_jobs(*_: object, **__: object) -> int:
        return 0

    monkeypatch.setattr(worker, "run_inline", no_jobs)
    url = "/api/internal/jobs/sweep"
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url, headers={"Authorization": "Bearer nope"})).status_code == 404
    res = await client.get(url, headers={"Authorization": "Bearer cron-secret"})
    assert res.status_code == 200
    assert res.json() == {"jobs": 0}


async def test_sweep_is_off_without_a_cron_secret(client: httpx.AsyncClient) -> None:
    res = await client.get("/api/internal/jobs/sweep", headers={"Authorization": "Bearer "})
    assert res.status_code == 404


def _request(headers: dict[str, str]) -> Request:
    raw = [(k.encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "headers": raw, "client": ("10.0.0.1", 1)})


def test_client_address_header_is_only_trusted_behind_the_proxy_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forged = {"x-client-ip": "1.2.3.4"}
    assert ratelimit.client_ip(_request(forged)) == "10.0.0.1"
    monkeypatch.setenv("API_PROXY_SECRET", "proxy-secret")
    get_settings.cache_clear()
    try:
        assert ratelimit.client_ip(_request(forged)) == "1.2.3.4"
    finally:
        monkeypatch.delenv("API_PROXY_SECRET")
        get_settings.cache_clear()
