"""Pipeline worker process.

For now: startup check, the loop, and graceful shutdown. Job claiming
(`FOR UPDATE SKIP LOCKED` on the `jobs` table) and the pipeline arrive in M4.

The idle loop must not query the database: a hosted database such as Neon scales
to zero only when nothing touches it, and a query every few seconds would keep it
awake (and billing compute) around the clock.
"""

import asyncio
import signal

import structlog

from returnguard import __version__, db
from returnguard.config import get_settings
from returnguard.log_config import configure_logging

log = structlog.get_logger(__name__)


async def run(stop: asyncio.Event) -> None:
    settings = get_settings()
    log.info(
        "worker.startup",
        version=__version__,
        poll_seconds=settings.worker_poll_seconds,
        **db.describe(db.database_url()),
    )
    try:
        await db.ping()
    except Exception as exc:
        # Keep running: the database may be waking up or briefly unreachable.
        log.warning("worker.database_unreachable", error=type(exc).__name__)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.worker_poll_seconds)
        except TimeoutError:
            pass
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
