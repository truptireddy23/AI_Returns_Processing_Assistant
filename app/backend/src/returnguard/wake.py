"""The API tells the worker "there's new work" over HTTP, not through the database.

A database channel (polling, or LISTEN/NOTIFY) would keep a scale-to-zero
database awake. This nudge is best-effort: if it's lost, the job is still in
the table and the worker's backstop sweep picks it up.
"""

import httpx
import structlog

from returnguard.config import get_settings

log = structlog.get_logger(__name__)


async def nudge_worker() -> None:
    url = get_settings().worker_wake_url
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.post(url)
    except httpx.HTTPError as exc:
        log.warning("wake.failed", error=type(exc).__name__)
