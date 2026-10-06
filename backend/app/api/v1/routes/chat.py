from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask a question over indexed documents",
)
async def chat(
    payload: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    """Retrieve relevant chunks and generate a grounded answer with sources."""
    service = ChatService(settings)
    return await service.ask(
        payload.question,
        filename=payload.filename,
        provider=payload.provider,
    )
