import asyncio

import pytest

from returnguard import jobs, worker
from returnguard.config import Settings
from returnguard.log_config import _redact_secrets


def quiet_settings(**overrides: object) -> Settings:
    # Port 0: let the OS pick a free port, so tests never clash with a running worker.
    return Settings(worker_wake_port=0, **overrides)  # type: ignore[arg-type]


@pytest.fixture
def drains(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count how often the worker looks for jobs (each look queries the database)."""
    calls: list[int] = []

    async def fake_drain(*_: object, **__: object) -> int:
        calls.append(1)
        return 0

    async def no_retries_due(*_: object) -> None:
        return None

    monkeypatch.setattr(worker, "drain", fake_drain)
    monkeypatch.setattr(jobs, "next_due_in", no_retries_due)
    monkeypatch.setattr(worker, "get_settings", quiet_settings)
    return calls


async def run_for(seconds: float) -> None:
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    await asyncio.sleep(seconds)
    stop.set()
    await asyncio.wait_for(task, timeout=1)


async def test_worker_stops_promptly_when_signalled(drains: list[int]) -> None:
    await run_for(0.05)


async def test_idle_worker_does_not_keep_querying_the_database(drains: list[int]) -> None:
    """A hosted database (Neon) only scales to zero if nothing touches it."""
    await run_for(0.3)
    assert len(drains) == 1  # the startup look only; the next is the 30-minute sweep


async def test_worker_comes_back_when_a_retry_is_due(
    drains: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    async def soon(*_: object) -> float:
        return 0.01

    monkeypatch.setattr(jobs, "next_due_in", soon)
    await run_for(0.8)  # the worker allows 0.5 s of slack after the due time
    assert len(drains) >= 2


async def test_worker_survives_database_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_drain(*_: object, **__: object) -> int:
        raise ConnectionRefusedError

    monkeypatch.setattr(worker, "drain", failing_drain)
    monkeypatch.setattr(worker, "get_settings", quiet_settings)
    await run_for(0.05)  # logs, waits, and still stops cleanly


async def _request(port: int, line: bytes) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(line + b"Host: worker\r\n\r\n")
    await writer.drain()
    response = await reader.read()
    writer.close()
    return response


async def test_wake_endpoint() -> None:
    wake = asyncio.Event()
    server = await asyncio.start_server(worker.wake_handler(wake), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        assert (await _request(port, b"GET /healthz HTTP/1.1\r\n")).startswith(b"HTTP/1.1 200")
        assert not wake.is_set()
        assert (await _request(port, b"GET /nope HTTP/1.1\r\n")).startswith(b"HTTP/1.1 404")
        assert (await _request(port, b"POST /wake HTTP/1.1\r\n")).startswith(b"HTTP/1.1 202")
        assert wake.is_set()
    finally:
        server.close()
        await server.wait_closed()


def test_secrets_are_redacted_from_log_events() -> None:
    event = {"event": "x", "api_key": "sk-123", "Authorization": "Bearer t", "user": "u1"}
    redacted = _redact_secrets(None, "info", dict(event))
    assert redacted["api_key"] == "[redacted]"
    assert redacted["Authorization"] == "[redacted]"
    assert redacted["user"] == "u1"
