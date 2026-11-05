"""FastAPI application: JSON API consumed by the Next.js frontend."""

import hmac
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Header, HTTPException, Response, status
from starlette.types import ASGIApp, Receive, Scope, Send

from returnguard import __version__, auth, db, worker
from returnguard.config import get_settings
from returnguard.log_config import configure_logging
from returnguard.ratelimit import PROXY_SECRET_HEADER
from returnguard.routers import admin, catalog, orders, returns, review
from returnguard.storage import get_storage

log = structlog.get_logger(__name__)

# Reachable without the proxy secret: Vercel Cron (which has its own secret) and
# platform health checks.
_OPEN_PATHS = {"/api/internal/jobs/sweep", "/api/healthz"}


class ProxyOnlyMiddleware:
    """With API_PROXY_SECRET set, answer 404 to anything that didn't come through
    the Next.js proxy, as if the API weren't publicly reachable at all."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        secret = get_settings().api_proxy_secret.get_secret_value()
        if secret and scope["type"] == "http" and scope["path"] not in _OPEN_PATHS:
            sent = dict(scope["headers"]).get(PROXY_SECRET_HEADER.encode(), b"")
            if not hmac.compare_digest(sent, secret.encode()):
                await Response(status_code=status.HTTP_404_NOT_FOUND)(scope, receive, send)
                return
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    log.info(
        "api.startup",
        version=__version__,
        environment=settings.environment,
        storage=get_storage().name,
        **db.describe(db.database_url()),
    )
    yield
    await db.dispose_engine()
    log.info("api.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ReturnGuard API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(ProxyOnlyMiddleware)
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
    app.include_router(auth.router)
    app.include_router(catalog.router)
    app.include_router(orders.router)
    app.include_router(returns.router)
    app.include_router(review.router)
    app.include_router(admin.router)

    @app.get("/api/internal/jobs/sweep", include_in_schema=False)
    async def sweep(authorization: Annotated[str, Header()] = "") -> dict[str, int]:
        """Backstop for serverless hosts: run any due jobs (called by Vercel Cron)."""
        secret = get_settings().cron_secret.get_secret_value()
        if not secret or not hmac.compare_digest(authorization, f"Bearer {secret}"):
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        done = await worker.run_inline(get_settings().inline_job_budget_seconds)
        log.info("worker.swept", jobs=done)
        return {"jobs": done}

    @app.get("/api/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok", "version": __version__}

    @app.get("/api/readyz", tags=["health"])
    async def readyz(response: Response) -> dict[str, str]:
        """Readiness: the process can reach its dependencies."""
        try:
            await db.ping()
        except Exception as exc:
            log.warning("readyz.database_unreachable", error=type(exc).__name__)
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return {"status": "unavailable", "database": "unreachable"}
        return {"status": "ok", "database": "ok"}

    return app


app = create_app()
