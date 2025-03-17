from fastapi import APIRouter

from app.api.endpoints import debug, health, ingestion

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
