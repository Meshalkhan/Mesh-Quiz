from typing import Protocol

from fastapi import status
from groq import AsyncGroq

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.chat import LlmProviderName

logger = get_logger(__name__)


class LLMProvider(Protocol):
    """Interface every LLM backend implements; services depend only on this."""

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str: ...


class GroqProvider:
    """Chat completions via the Groq API (open models)."""

    def __init__(self, *, api_key: str, model: str) -> None:
        if not api_key.strip():
            raise AppError(
                "GROQ_API_KEY is not configured",
                code="llm_not_configured",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as exc:
            logger.exception(
                "llm_generate_failed provider=groq model=%s",
                self._model,
            )
            raise AppError(
                "Failed to generate an answer from the LLM",
                code="llm_error",
                status_code=status.HTTP_502_BAD_GATEWAY,
                details=[{"reason": str(exc)}],
            ) from exc

        content = response.choices[0].message.content if response.choices else None
        if not content or not content.strip():
            raise AppError(
                "LLM returned an empty response",
                code="llm_empty_response",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )
        return content.strip()


def provider_availability(settings: Settings) -> dict[LlmProviderName, bool]:
    """Which providers have credentials configured. New providers register here."""
    return {"groq": bool(settings.groq_api_key.strip())}


def default_provider_name(settings: Settings) -> LlmProviderName:
    selected = settings.llm_provider.lower().strip()
    for name in provider_availability(settings):
        if name == selected:
            return name
    return "groq"


def create_llm_provider(
    settings: Settings, provider: str | None = None
) -> LLMProvider:
    selected = (provider or settings.llm_provider).lower().strip()

    if selected == "groq":
        return GroqProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )

    raise AppError(
        f"Unsupported LLM provider: {provider or settings.llm_provider}",
        code="unsupported_llm_provider",
        status_code=status.HTTP_400_BAD_REQUEST,
    )
