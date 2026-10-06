import asyncio
from uuid import uuid4

import chromadb
from fastapi import status

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.document import ChunkMetadata, DocumentChunk, SimilarityResult

logger = get_logger(__name__)


class VectorStore:
    """Persists document chunks in ChromaDB and runs similarity search."""

    def __init__(self, settings: Settings) -> None:
        self._collection_name = settings.chroma_collection_name
        self._client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_documents(self, chunks: list[DocumentChunk]) -> list[str]:
        if not chunks:
            raise AppError(
                "No document chunks provided for indexing",
                code="empty_chunks",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        ids = [uuid4().hex for _ in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "filename": chunk.metadata.filename,
                "page_number": chunk.metadata.page_number,
            }
            for chunk in chunks
        ]

        try:
            await asyncio.to_thread(
                self._collection.add,
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            logger.exception("vector_add_failed collection=%s", self._collection_name)
            raise AppError(
                "Failed to store document embeddings",
                code="vector_store_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=[{"reason": str(exc)}],
            ) from exc

        logger.info(
            "documents_indexed collection=%s count=%s",
            self._collection_name,
            len(ids),
        )
        return ids

    async def list_documents(self) -> list[tuple[str, int]]:
        try:
            raw = await asyncio.to_thread(
                self._collection.get,
                include=["metadatas"],
            )
        except Exception as exc:
            logger.exception(
                "vector_list_failed collection=%s", self._collection_name
            )
            raise AppError(
                "Failed to list indexed documents",
                code="vector_list_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=[{"reason": str(exc)}],
            ) from exc

        counts: dict[str, int] = {}
        for metadata in raw.get("metadatas") or []:
            if not metadata:
                continue
            name = str(metadata.get("filename", "")).strip()
            if not name:
                continue
            counts[name] = counts.get(name, 0) + 1

        return sorted(counts.items(), key=lambda item: item[0].lower())

    async def search_documents(
        self,
        query: str,
        *,
        top_k: int = 5,
        filename: str | None = None,
    ) -> list[SimilarityResult]:
        normalized_query = query.strip()
        if not normalized_query:
            raise AppError(
                "Search query must not be empty",
                code="empty_query",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if top_k <= 0:
            raise AppError(
                "top_k must be greater than zero",
                code="invalid_top_k",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        where: dict[str, str] | None = None
        scoped_name = (filename or "").strip()
        if scoped_name:
            where = {"filename": scoped_name}
            matching = await asyncio.to_thread(
                self._collection.get,
                where=where,
                include=[],
            )
            match_count = len(matching.get("ids") or [])
            if match_count == 0:
                return []
            top_k = min(top_k, match_count)

        try:
            query_kwargs: dict[str, object] = {
                "query_texts": [normalized_query],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where is not None:
                query_kwargs["where"] = where
            raw = await asyncio.to_thread(self._collection.query, **query_kwargs)
        except Exception as exc:
            logger.exception(
                "vector_search_failed collection=%s", self._collection_name
            )
            raise AppError(
                "Failed to search document embeddings",
                code="vector_search_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=[{"reason": str(exc)}],
            ) from exc

        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        results: list[SimilarityResult] = []
        for content, metadata, distance in zip(
            documents, metadatas, distances, strict=False
        ):
            if content is None or metadata is None:
                continue
            results.append(
                SimilarityResult(
                    content=content,
                    metadata=ChunkMetadata(
                        filename=str(metadata.get("filename", "")),
                        page_number=int(metadata.get("page_number", 1)),
                    ),
                    distance=float(distance),
                )
            )

        logger.info(
            "documents_searched collection=%s query_length=%s filename=%s results=%s",
            self._collection_name,
            len(normalized_query),
            scoped_name or "*",
            len(results),
        )
        return results

    async def delete_by_filename(self, filename: str) -> int:
        scoped_name = filename.strip()
        if not scoped_name:
            raise AppError(
                "Filename is required",
                code="invalid_filename",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        where = {"filename": scoped_name}
        try:
            matching = await asyncio.to_thread(
                self._collection.get,
                where=where,
                include=[],
            )
            ids = matching.get("ids") or []
            if not ids:
                return 0
            await asyncio.to_thread(self._collection.delete, ids=ids)
        except Exception as exc:
            logger.exception(
                "vector_delete_failed collection=%s filename=%s",
                self._collection_name,
                scoped_name,
            )
            raise AppError(
                "Failed to delete document embeddings",
                code="vector_delete_error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=[{"reason": str(exc)}],
            ) from exc

        logger.info(
            "documents_deleted collection=%s filename=%s count=%s",
            self._collection_name,
            scoped_name,
            len(ids),
        )
        return len(ids)
