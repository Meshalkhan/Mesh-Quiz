from fastapi import APIRouter

from app.api.v1.routes import chat, documents, health
from app.core.config import Settings


def create_api_router(settings: Settings) -> APIRouter:
    """Mount versioned routes directly to avoid nested include_router issues."""
    api_router = APIRouter(prefix=settings.api_v1_prefix)
    api_router.include_router(health.router)
    api_router.include_router(documents.router)
    api_router.include_router(chat.router)
    return api_router
