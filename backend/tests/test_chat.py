import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas.document import ChunkMetadata, SimilarityResult
from app.services import chat as chat_module
from app.services.chat import NO_CONTEXT_ANSWER, ChatService


class FakeVectorStore:
    results: list[SimilarityResult] = []

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def search_documents(
        self, query: str, *, top_k: int = 5, filename: str | None = None
    ) -> list[SimilarityResult]:
        return list(self.results)


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        return "grounded answer"


def _result(distance: float) -> SimilarityResult:
    return SimilarityResult(
        content="Photosynthesis converts light into chemical energy.",
        metadata=ChunkMetadata(filename="bio.pdf", page_number=3),
        distance=distance,
    )


@pytest.fixture
def fake_store(monkeypatch: pytest.MonkeyPatch) -> type[FakeVectorStore]:
    monkeypatch.setattr(FakeVectorStore, "results", [])
    monkeypatch.setattr(chat_module, "VectorStore", FakeVectorStore)
    return FakeVectorStore


@pytest.fixture
def llm_must_not_be_called(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        raise AssertionError("LLM must not be called without relevant context")

    monkeypatch.setattr(chat_module, "create_llm_provider", fail)


@pytest.mark.usefixtures("llm_must_not_be_called")
def test_refuses_when_nothing_is_retrieved(
    settings: Settings, fake_store: type[FakeVectorStore]
) -> None:
    response = asyncio.run(ChatService(settings).ask("What is photosynthesis?"))

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.sources == []


@pytest.mark.usefixtures("llm_must_not_be_called")
def test_refuses_when_results_exceed_distance_cutoff(
    settings: Settings, fake_store: type[FakeVectorStore]
) -> None:
    fake_store.results = [_result(settings.retrieval_max_distance + 0.1)]

    response = asyncio.run(ChatService(settings).ask("What is photosynthesis?"))

    assert response.answer == NO_CONTEXT_ANSWER
    assert response.sources == []


@pytest.mark.usefixtures("llm_must_not_be_called")
def test_chat_route_refuses_without_context(
    client: TestClient, fake_store: type[FakeVectorStore]
) -> None:
    response = client.post(
        "/api/v1/chat", json={"question": "Anything?", "filename": "bio.pdf"}
    )

    assert response.status_code == 200
    assert response.json() == {"answer": NO_CONTEXT_ANSWER, "sources": []}


def test_answers_with_sources_when_context_is_relevant(
    settings: Settings,
    fake_store: type[FakeVectorStore],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_store.results = [_result(0.2), _result(0.3)]
    llm = FakeLLM()
    monkeypatch.setattr(chat_module, "create_llm_provider", lambda *_: llm)

    response = asyncio.run(ChatService(settings).ask("What is photosynthesis?"))

    assert llm.calls == 1
    assert response.answer == "grounded answer"
    assert [s.model_dump() for s in response.sources] == [
        {"filename": "bio.pdf", "page_number": 3}
    ]


def test_chat_rejects_unknown_provider(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat", json={"question": "Anything?", "provider": "bedrock"}
    )

    assert response.status_code == 422
