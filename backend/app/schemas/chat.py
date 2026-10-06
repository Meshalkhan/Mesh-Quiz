from typing import Literal

from pydantic import BaseModel, Field

# Bedrock joins this union when its provider is added.
LlmProviderName = Literal["groq"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1)
    filename: str | None = Field(
        default=None,
        description="When set, retrieve only chunks from this uploaded filename.",
    )
    provider: LlmProviderName | None = Field(
        default=None,
        description="Optional LLM provider override. Defaults to server LLM_PROVIDER.",
    )


class ChatSource(BaseModel):
    filename: str
    page_number: int = Field(ge=1)


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
