"""MarketingOS - administration back-office.

A standalone FastAPI app rather than a router bolted onto the product's, and
the isolation is the point. Its own CORS allowlist, its own routes, its own
signing secret, its own Lambda, its own bucket and distribution. It shares one
thing with the platform: the database, which is the only place the truth about
a customer lives.

A bug in the product cannot expose this surface, and a stolen customer token
cannot read it.
"""

from __future__ import annotations

import logging

from app.core.database import engine
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import get_admin_settings
from .routers import admins, auth, overview, users

settings = get_admin_settings()
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("marketingos.admin")

app = FastAPI(
    title="MarketingOS - Administration",
    version="1.0.0",
    # No interactive docs in production. They are a map of every route that
    # changes a customer account, served to anyone who finds the hostname.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


for router in (auth.router, overview.router, users.router, admins.router, admins.audit_router):
    app.include_router(router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Log the detail, return none of it.

    A stack trace in a response body from the console that manages every
    customer account is free reconnaissance.
    """
    logger.exception("admin_unhandled_exception path=%s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error."})


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health() -> dict:
    checks = {"database": "ok"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - the point is to report, not to raise.
        checks["database"] = "unreachable"
    return {"status": "ok" if checks["database"] == "ok" else "degraded", "checks": checks}


def _lambda_handler():
    """Wrap the app for API Gateway, if it is being run there.

    Mangum is an optional import so `uvicorn admin.main:app` still works on a
    laptop with nothing extra installed, and so a missing dependency in the
    Lambda bundle fails with a sentence rather than an ImportError at cold
    start.
    """
    try:
        from mangum import Mangum
    except ImportError:  # pragma: no cover - only reachable in a broken bundle

        def _missing(event, context):
            raise RuntimeError("mangum is required to run the back-office on Lambda.")

        return _missing
    # lifespan="off": there is no startup work here, and Mangum's lifespan
    # emulation would run it on every cold start for nothing.
    return Mangum(app, lifespan="off")


lambda_handler = _lambda_handler()
