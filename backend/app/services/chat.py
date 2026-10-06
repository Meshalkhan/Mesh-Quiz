from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.chat import ChatResponse, ChatSource
from app.schemas.document import SimilarityResult
from app.services.llm import create_llm_provider
from app.services.vector_store import VectorStore

logger = get_logger(__name__)

NO_CONTEXT_ANSWER = "I couldn't find relevant information."

SYSTEM_PROMPT = """You are Mesh Quiz, a document question answering assistant.

Rules:
- Answer using only the provided context.
- Do not invent facts or speculate.
- If the context does not contain enough information to answer, reply exactly:
I couldn't find relevant information.
- Keep answers concise and grounded in the context.
"""


class ChatService:
    """Retrieves context and generates grounded answers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._vector_store = VectorStore(settings)

    async def ask(
        self,
        question: str,
        *,
        filename: str | None = None,
        provider: str | None = None,
    ) -> ChatResponse:
        normalized_question = question.strip()
        scoped_filename = (filename or "").strip() or None
        results = await self._vector_store.search_documents(
            normalized_question,
            top_k=self._settings.retrieval_top_k,
            filename=scoped_filename,
        )
        relevant = [
            result
            for result in results
            if result.distance <= self._settings.retrieval_max_distance
        ]

        sources = self._build_sources(relevant)
        if not relevant:
            logger.info(
                "chat_no_relevant_context question_length=%s filename=%s",
                len(normalized_question),
                scoped_filename or "*",
            )
            return ChatResponse(answer=NO_CONTEXT_ANSWER, sources=sources)

        llm = create_llm_provider(self._settings, provider)
        answer = await llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=self._build_user_prompt(normalized_question, relevant),
        )
        logger.info(
            "chat_answered question_length=%s sources=%s provider=%s",
            len(normalized_question),
            len(sources),
            (provider or self._settings.llm_provider).lower().strip(),
        )
        return ChatResponse(answer=answer, sources=sources)

    def _build_user_prompt(self, question: str, results: list[SimilarityResult]) -> str:
        context_blocks: list[str] = []
        for index, result in enumerate(results, start=1):
            context_blocks.append(
                "\n".join(
                    [
                        f"[{index}] filename={result.metadata.filename} "
                        f"page={result.metadata.page_number}",
                        result.content,
                    ]
                )
            )
        context = "\n\n".join(context_blocks)
        return (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the context above."
        )

    def _build_sources(self, results: list[SimilarityResult]) -> list[ChatSource]:
        seen: set[tuple[str, int]] = set()
        sources: list[ChatSource] = []
        for result in results:
            key = (result.metadata.filename, result.metadata.page_number)
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                ChatSource(
                    filename=result.metadata.filename,
                    page_number=result.metadata.page_number,
                )
            )
        return sources
