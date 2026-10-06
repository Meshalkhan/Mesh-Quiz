from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.health import HealthResponse, LlmProviderAvailability
from app.services.llm import default_provider_name, provider_availability

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        default_llm_provider=default_provider_name(settings),
        llm_providers=[
            LlmProviderAvailability(name=name, configured=configured)
            for name, configured in provider_availability(settings).items()
        ],
    )
