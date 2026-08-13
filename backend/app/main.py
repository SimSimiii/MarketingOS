import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.orchestration.execution_manager import reap_orphaned_executions

settings = get_settings()
logger = logging.getLogger("marketingos.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # A run left RUNNING can only mean the previous process died mid-campaign
    # (crash, restart) - there is no in-memory registry entry for it in this
    # process, so it can never finish or be cancelled. Fail it explicitly
    # instead of leaving a campaign stuck "running" forever.
    reaped = reap_orphaned_executions()
    if reaped:
        logger.warning("Reaped %d orphaned execution(s) from a previous run", reaped)
    yield


app = FastAPI(title="MarketingOS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
