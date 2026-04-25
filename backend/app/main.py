"""FastAPI application entry point."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware.auth import RequestIDMiddleware
from app.middleware.rate_limit import limiter

log = structlog.get_logger()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log.info("startup", env=settings.app_env)

    # Initialize DB connection pool (non-fatal if DB not available in dev)
    from app.db import engine
    try:
        async with engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        log.info("db_connected")
    except Exception as exc:
        log.warning("db_not_available", error=str(exc))

    # Ensure object storage bucket exists (non-fatal, 10s timeout)
    import asyncio
    from app.adapters.storage import StorageAdapter
    try:
        await asyncio.wait_for(StorageAdapter().ensure_bucket(), timeout=10)
    except Exception as exc:
        log.warning("storage_init_failed", error=str(exc))

    yield

    # Shutdown
    from app.db import engine
    await engine.dispose()
    log.info("shutdown")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HistoryLive API",
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── State ─────────────────────────────────────────────────────────────────
    app.state.limiter = limiter

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limit error handler ──────────────────────────────────────────────
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Custom exception handlers ─────────────────────────────────────────────
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", "http_error")
            message = detail.get("message", str(exc.detail))
            retryable = detail.get("retryable", False)
        else:
            code = "http_error"
            message = str(detail)
            retryable = False
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                    "retryable": retryable,
                }
            },
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request body validation failed.",
                    "request_id": request_id,
                    "retryable": False,
                    "detail": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        log.exception("unhandled_error", request_id=request_id, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id,
                    "retryable": True,
                }
            },
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.api import auth, sessions, research, script, seed, storyboard, media, artifacts, events, speeches, admin, bust

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(sessions.router, prefix=prefix)
    app.include_router(research.router, prefix=prefix)
    app.include_router(script.router, prefix=prefix)
    app.include_router(seed.router, prefix=prefix)
    app.include_router(storyboard.router, prefix=prefix)
    app.include_router(bust.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(artifacts.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(speeches.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
