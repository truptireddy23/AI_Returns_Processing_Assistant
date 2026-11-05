"""Rate limiting for public write endpoints (login now; checkout and returns later).

Counters live in process memory, which is correct for the single API process we
run. Running several API replicas would need a shared store (e.g. Redis); see
docs/safety_privacy.md.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status
from limits import RateLimitItem, parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from returnguard.config import get_settings

_storage = MemoryStorage()
_limiter = MovingWindowRateLimiter(_storage)


PROXY_SECRET_HEADER = "x-proxy-secret"  # noqa: S105  (a header name)
CLIENT_IP_HEADER = "x-client-ip"


def client_ip(request: Request) -> str:
    # With API_PROXY_SECRET set (hosted, e.g. Vercel), every request was checked to
    # come from the Next.js proxy, which passes the browser's address in its own
    # header. Otherwise Uvicorn runs with --proxy-headers, so this is the browser's
    # address as forwarded by the Next.js server, not the proxy's.
    if get_settings().api_proxy_secret.get_secret_value():
        forwarded = request.headers.get(CLIENT_IP_HEADER)
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


async def _too_many(item: RateLimitItem, scope: str, key: str) -> HTTPException:
    stats = await _limiter.get_window_stats(item, scope, key)
    retry_after = max(1, int(stats.reset_time - time.time()))
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many attempts. Please wait and try again.",
        headers={"Retry-After": str(retry_after)},
    )


def rate_limit(limit: str, scope: str) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency: allow `limit` (e.g. "5/minute") requests per client IP.

    The client IP comes from X-Forwarded-For, which a client can forge unless a
    trusted reverse proxy overwrites it, so sensitive endpoints also need a
    per-account limit (`FailureLimit`).
    """
    item = parse(limit)

    async def dependency(request: Request) -> None:
        key = client_ip(request)
        if not await _limiter.hit(item, scope, key):
            raise await _too_many(item, scope, key)

    return dependency


class FailureLimit:
    """Counts failures per key (e.g. per account) and blocks once over `limit`.

    Unlike the per-IP limit this can't be dodged by changing address, and
    successful attempts don't count against it.
    """

    def __init__(self, limit: str, scope: str) -> None:
        self.item = parse(limit)
        self.scope = scope

    async def check(self, key: str) -> None:
        """Raise 429 if `key` has used up its failures."""
        if not await _limiter.test(self.item, self.scope, key):
            raise await _too_many(self.item, self.scope, key)

    async def record_failure(self, key: str) -> None:
        await _limiter.hit(self.item, self.scope, key)


def reset() -> None:
    """Clear all counters (tests) by starting from empty storage."""
    global _storage, _limiter
    _storage = MemoryStorage()
    _limiter = MovingWindowRateLimiter(_storage)
