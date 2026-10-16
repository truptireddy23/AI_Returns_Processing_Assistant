import asyncio

import pytest

from returnguard import db, worker
from returnguard.config import Settings
from returnguard.log_config import _redact_secrets


async def test_worker_stops_promptly_when_signalled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ping() -> None:
        return None

    monkeypatch.setattr(db, "ping", fake_ping)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1)


async def test_worker_survives_database_outage(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    async def failing_ping() -> None:
        nonlocal calls
        calls += 1
        raise ConnectionRefusedError

    monkeypatch.setattr(db, "ping", failing_ping)
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    await asyncio.sleep(0.05)
    stop.set()
    await asyncio.wait_for(task, timeout=1)
    assert calls >= 1


async def test_idle_worker_does_not_keep_querying_the_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hosted database (Neon) only scales to zero if nothing touches it."""
    calls = 0

    async def counting_ping() -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(db, "ping", counting_ping)
    monkeypatch.setattr(worker, "get_settings", lambda: Settings(worker_poll_seconds=0.01))
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    await asyncio.sleep(0.2)  # ~20 idle loops
    stop.set()
    await asyncio.wait_for(task, timeout=1)
    assert calls == 1  # the startup check only


def test_secrets_are_redacted_from_log_events() -> None:
    event = {"event": "x", "api_key": "sk-123", "Authorization": "Bearer t", "user": "u1"}
    redacted = _redact_secrets(None, "info", dict(event))
    assert redacted["api_key"] == "[redacted]"
    assert redacted["Authorization"] == "[redacted]"
    assert redacted["user"] == "u1"
