"""FastAPI application: JSON API consumed by the Next.js frontend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Response, status

from returnguard import __version__, auth, db
from returnguard.config import get_settings
from returnguard.log_config import configure_logging
from returnguard.routers import admin, orders, review

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)
    log.info("api.startup", version=__version__, environment=settings.environment)
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
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
    app.include_router(auth.router)
    app.include_router(orders.router)
    app.include_router(review.router)
    app.include_router(admin.router)

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
