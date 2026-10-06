import asyncio
from pathlib import Path

from fastapi import status
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.document import ChunkMetadata, DocumentChunk

logger = get_logger(__name__)


class DocumentProcessor:
    """Extracts text from a PDF and splits it into configurable chunks."""

    def __init__(self, settings: Settings) -> None:
        self._chunk_size = settings.chunk_size
        self._chunk_overlap = settings.chunk_overlap

    async def process(self, file_path: Path, filename: str) -> list[DocumentChunk]:
        pages = await asyncio.to_thread(self._extract_pages, file_path)
        chunks = self._split_pages(pages, filename)
        logger.info(
            "document_processed filename=%s pages=%s chunks=%s chunk_size=%s",
            filename,
            len(pages),
            len(chunks),
            self._chunk_size,
        )
        return chunks

    def _extract_pages(self, file_path: Path) -> list[tuple[int, str]]:
        try:
            reader = PdfReader(str(file_path))
        except PdfReadError as exc:
            logger.warning("invalid_pdf path=%s error=%s", file_path, exc)
            raise AppError(
                "Unable to read PDF file",
                code="invalid_pdf",
                status_code=status.HTTP_400_BAD_REQUEST,
                details=[{"path": str(file_path), "reason": str(exc)}],
            ) from exc
        except OSError as exc:
            logger.exception("pdf_read_failed path=%s", file_path)
            raise AppError(
                "Failed to open uploaded PDF",
                code="pdf_read_failed",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=[{"path": str(file_path)}],
            ) from exc

        if len(reader.pages) == 0:
            raise AppError(
                "PDF contains no pages",
                code="empty_pdf",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        pages: list[tuple[int, str]] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                logger.warning(
                    "page_extract_failed path=%s page=%s error=%s",
                    file_path,
                    index,
                    exc,
                )
                raise AppError(
                    f"Failed to extract text from page {index}",
                    code="pdf_extract_failed",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    details=[{"page_number": index, "reason": str(exc)}],
                ) from exc
            pages.append((index, text))

        if not any(text.strip() for _, text in pages):
            raise AppError(
                "No extractable text found in PDF",
                code="no_pdf_text",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return pages

    def _split_pages(
        self, pages: list[tuple[int, str]], filename: str
    ) -> list[DocumentChunk]:
        if self._chunk_size <= 0:
            raise AppError(
                "Chunk size must be greater than zero",
                code="invalid_chunk_size",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        overlap = max(0, min(self._chunk_overlap, self._chunk_size - 1))
        chunks: list[DocumentChunk] = []

        for page_number, text in pages:
            normalized = " ".join(text.split())
            if not normalized:
                continue

            start = 0
            while start < len(normalized):
                end = start + self._chunk_size
                content = normalized[start:end].strip()
                if content:
                    chunks.append(
                        DocumentChunk(
                            content=content,
                            metadata=ChunkMetadata(
                                filename=filename,
                                page_number=page_number,
                            ),
                        )
                    )

                if end >= len(normalized):
                    break
                start = end - overlap

        return chunks
