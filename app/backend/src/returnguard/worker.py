"""Pipeline worker process.

Waits for a wake-up (an HTTP POST from the API on the internal network), the
next retry coming due, or the backstop sweep; then drains every due job.

While idle it does not touch the database at all, so a scale-to-zero database
such as Neon can suspend. Wake-ups carry no data and need no auth: the port is
only reachable inside the Docker network, and the worst a stray request can do
is make the worker look for jobs.
"""

import asyncio
import random
import signal
from collections.abc import Awaitable, Callable

import structlog

from returnguard import __version__, db, jobs
from returnguard.config import get_settings
from returnguard.log_config import configure_logging
from returnguard.pipeline.runner import mark_pipeline_failed, review_return
from returnguard.pipeline.steps import RuleSteps, Steps

log = structlog.get_logger(__name__)

_RESPONSES = {
    "wake": b"HTTP/1.1 202 Accepted\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
    "health": b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok",
    "missing": b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
}


def wake_handler(
    wake: asyncio.Event,
) -> Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]:
    """A deliberately tiny HTTP endpoint: POST /wake and GET /healthz."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=2)
            method, path, *_ = [*line.decode("latin-1").split(), "", ""]
            if method == "POST" and path == "/wake":
                wake.set()
                writer.write(_RESPONSES["wake"])
            elif method == "GET" and path == "/healthz":
                writer.write(_RESPONSES["health"])
            else:
                writer.write(_RESPONSES["missing"])
            await writer.drain()
        except (TimeoutError, ConnectionError, UnicodeDecodeError):
            pass
        finally:
            writer.close()

    return handle


async def process_one(steps: Steps, rng: random.Random | None = None) -> bool:
    """Claim and run one due job. Returns False when there was nothing to do."""
    async for session in db.get_session():
        job = await jobs.claim_next(session)
        if job is None:
            return False
        job_id, return_id, attempt, kind = job.id, job.return_id, job.attempts, job.kind
        log.info("worker.job_started", job_id=str(job_id), attempt=attempt)
        try:
            if kind == jobs.REVIEW_JOB and return_id is not None:
                await review_return(session, return_id, steps=steps, rng=rng)
            else:
                raise ValueError(f"Unknown job kind: {kind}")
        except Exception as exc:
            await session.rollback()
            error = f"{type(exc).__name__}: {exc}"
            log.exception("worker.job_error", job_id=str(job_id), attempt=attempt)
            if await jobs.fail(session, job_id, error) and return_id is not None:
                await mark_pipeline_failed(session, return_id, error)
            return True
        await jobs.complete(session, job_id)
        log.info("worker.job_done", job_id=str(job_id))
    return True


async def drain(steps: Steps, rng: random.Random | None = None) -> int:
    done = 0
    while await process_one(steps, rng):
        done += 1
    return done


async def run(stop: asyncio.Event, *, steps: Steps | None = None) -> None:
    settings = get_settings()
    steps = steps or RuleSteps()
    wake = asyncio.Event()
    server = await asyncio.start_server(
        wake_handler(wake),
        "0.0.0.0",  # noqa: S104  (reachable only inside the Docker network)
        settings.worker_wake_port,
    )
    log.info(
        "worker.startup",
        version=__version__,
        wake_port=settings.worker_wake_port,
        sweep_seconds=settings.worker_sweep_seconds,
        steps=getattr(steps, "source", type(steps).__name__),
        **db.describe(db.database_url()),
    )
    wake.set()  # look for a backlog once at startup
    try:
        while not stop.is_set():
            timeout = settings.worker_sweep_seconds
            if wake.is_set():
                wake.clear()
                try:
                    done = await drain(steps)
                    if done:
                        log.info("worker.drained", jobs=done)
                    async for session in db.get_session():
                        due = await jobs.next_due_in(session)
                    if due is not None:
                        timeout = min(timeout, due + 0.5)
                except Exception as exc:
                    # Database waking up or briefly unreachable: try again shortly.
                    log.warning("worker.database_unreachable", error=type(exc).__name__)
                    timeout = min(timeout, 10.0)
            waiters = [asyncio.ensure_future(stop.wait()), asyncio.ensure_future(wake.wait())]
            await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
            for task in waiters:
                task.cancel()
            if not stop.is_set():
                wake.set()  # woken, a retry came due, or the sweep: look for work
    finally:
        server.close()
        await server.wait_closed()
        await db.dispose_engine()
        log.info("worker.shutdown")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    async def _main() -> None:
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop.set)
        await run(stop)

    asyncio.run(_main())


if __name__ == "__main__":
    main()
