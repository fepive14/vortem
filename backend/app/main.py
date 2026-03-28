"""FastAPI application factory and lifespan."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging(settings.ENVIRONMENT, settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown logic."""
    logger.info(
        "startup",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Vortem CRM API",
    version="0.1.0",
    description="On-premise CRM backend.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # Required for cookie-based auth.
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request ID middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Bind a unique request_id to every log record in this request's context."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(v1_router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Liveness probe for load balancers and container orchestrators."""
    return {"status": "ok"}
