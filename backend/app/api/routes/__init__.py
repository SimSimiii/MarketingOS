from fastapi import APIRouter

from app.api.routes import (
    brands,
    campaigns,
    executions,
    health,
    knowledge,
    logs,
    market,
    models,
    settings,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(brands.router)
api_router.include_router(campaigns.router)
api_router.include_router(executions.router)
api_router.include_router(knowledge.router)
api_router.include_router(market.router)
api_router.include_router(models.router)
api_router.include_router(settings.router)
api_router.include_router(logs.router)
