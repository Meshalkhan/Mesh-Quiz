import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.llm import GroqProvider, create_llm_provider


def test_groq_is_created_when_key_is_set(settings: Settings) -> None:
    configured = settings.model_copy(update={"groq_api_key": "test-key"})

    assert isinstance(create_llm_provider(configured), GroqProvider)


def test_groq_without_key_is_rejected(settings: Settings) -> None:
    with pytest.raises(AppError) as exc_info:
        create_llm_provider(settings)

    assert exc_info.value.code == "llm_not_configured"


def test_unknown_provider_is_rejected(settings: Settings) -> None:
    with pytest.raises(AppError) as exc_info:
        create_llm_provider(settings, "bedrock")

    assert exc_info.value.code == "unsupported_llm_provider"
