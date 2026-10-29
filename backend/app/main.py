import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import engine, init_db
from app.orchestration.execution_manager import reap_orphaned_executions
from app.runtime.work_limits import WorkLimitError
from app.services.credit_service import assert_payment_mode_safe
from app.services.email_analysis_service import reap_email_analyses
from app.services.linkedin_service import reap_linkedin_runs

settings = get_settings()
logger = logging.getLogger("marketingos.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.credit_billing_enabled:
        with Session(engine) as session:
            assert_payment_mode_safe(
                session, live=settings.stripe_secret_key.startswith("sk_live_")
            )
    reap_linkedin_runs(engine)
    reap_email_analyses(engine)
    # A run left RUNNING can only mean the previous process died mid-campaign
    # (crash, restart) - there is no in-memory registry entry for it in this
    # process, so it can never finish or be cancelled. Fail it explicitly
    # instead of leaving a campaign stuck "running" forever.
    reaped = reap_orphaned_executions()
    if reaped:
        logger.warning("Reaped %d orphaned execution(s) from a previous run", reaped)
    yield


app = FastAPI(title="MarketingOS API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(WorkLimitError)
async def work_limit_error(request, exc: WorkLimitError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)

_SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
)


class SecurityHeadersMiddleware:
    """The back-office's hardening headers, on every API response.

    Plain ASGI rather than `@app.middleware("http")`: that wrapper buffers
    through a memory stream, and the execution SSE feed has to reach the
    browser event by event.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def with_headers(message):
            if message["type"] == "http.response.start":
                present = {name.lower() for name, _ in message.get("headers", [])}
                message["headers"] = [
                    *message.get("headers", []),
                    *((name, value) for name, value in _SECURITY_HEADERS if name not in present),
                ]
            await send(message)

        return await self.app(scope, receive, with_headers)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
