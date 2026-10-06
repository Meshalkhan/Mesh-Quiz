from typing import Literal

from pydantic import BaseModel

from app.schemas.chat import LlmProviderName


class LlmProviderAvailability(BaseModel):
    name: LlmProviderName
    configured: bool


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str
    default_llm_provider: LlmProviderName
    llm_providers: list[LlmProviderAvailability]
