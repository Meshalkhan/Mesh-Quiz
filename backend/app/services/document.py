import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.schemas.document import (
    DocumentDeleteData,
    DocumentListData,
    DocumentSummary,
    DocumentUploadData,
)
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStore

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = frozenset({"application/pdf"})
PDF_MAGIC = b"%PDF"


class DocumentService:
    """Handles temporary PDF upload storage and validation."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._upload_dir = Path(settings.upload_dir)
        self._processor = DocumentProcessor(settings)
        self._vector_store = VectorStore(settings)

    async def list_documents(self) -> DocumentListData:
        items = await self._vector_store.list_documents()
        return DocumentListData(
            documents=[
                DocumentSummary(filename=name, chunk_count=count)
                for name, count in items
            ]
        )

    async def delete_document(self, filename: str) -> DocumentDeleteData:
        safe_name = self._validate_filename(filename)
        deleted_chunks = await self._vector_store.delete_by_filename(safe_name)
        if deleted_chunks == 0:
            raise AppError(
                "Document not found",
                code="document_not_found",
                status_code=status.HTTP_404_NOT_FOUND,
                details=[{"filename": safe_name}],
            )

        deleted_files = await self._delete_stored_files(safe_name)
        logger.info(
            "document_deleted filename=%s chunks=%s files=%s",
            safe_name,
            deleted_chunks,
            deleted_files,
        )
        return DocumentDeleteData(
            filename=safe_name,
            deleted_chunks=deleted_chunks,
            deleted_files=deleted_files,
        )

    async def _delete_stored_files(self, filename: str) -> int:
        if not self._upload_dir.exists():
            return 0

        matches = [
            path
            for path in self._upload_dir.iterdir()
            if path.is_file() and path.name.endswith(f"_{filename}")
        ]

        deleted = 0
        for path in matches:
            try:
                await asyncio.to_thread(path.unlink)
                deleted += 1
            except OSError as exc:
                logger.warning(
                    "document_file_delete_failed path=%s reason=%s",
                    path,
                    exc,
                )
        return deleted

    async def upload_pdf(self, file: UploadFile) -> DocumentUploadData:
        filename = self._validate_filename(file.filename)
        content_type = self._validate_content_type(file.content_type)
        content = await file.read()
        size = len(content)

        self._validate_size(size)
        self._validate_pdf_content(content)

        stored_path = await self._save_file(filename, content)
        logger.info(
            "document_uploaded filename=%s size=%s path=%s",
            filename,
            size,
            stored_path,
        )

        chunks = await self._processor.process(stored_path, filename)
        ids = await self._vector_store.add_documents(chunks)

        return DocumentUploadData(
            filename=filename,
            size=size,
            content_type=content_type,
            status="indexed",
            chunks=chunks,
            indexed_count=len(ids),
        )

    def _validate_filename(self, filename: str | None) -> str:
        if not filename or not filename.strip():
            raise AppError(
                "Filename is required",
                code="invalid_filename",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        safe_name = Path(filename).name
        if not safe_name.lower().endswith(".pdf"):
            raise AppError(
                "Only PDF files are supported",
                code="invalid_file_type",
                status_code=status.HTTP_400_BAD_REQUEST,
                details=[{"filename": safe_name}],
            )
        return safe_name

    def _validate_content_type(self, content_type: str | None) -> str:
        normalized = (content_type or "").split(";")[0].strip().lower()
        if normalized not in ALLOWED_CONTENT_TYPES:
            raise AppError(
                "Only PDF files are supported",
                code="invalid_file_type",
                status_code=status.HTTP_400_BAD_REQUEST,
                details=[{"content_type": content_type}],
            )
        return normalized

    def _validate_size(self, size: int) -> None:
        if size == 0:
            raise AppError(
                "Uploaded file is empty",
                code="empty_file",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if size > self._settings.max_upload_bytes:
            raise AppError(
                "Uploaded file exceeds the maximum allowed size",
                code="file_too_large",
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                details=[
                    {
                        "size": size,
                        "max_upload_bytes": self._settings.max_upload_bytes,
                    }
                ],
            )

    def _validate_pdf_content(self, content: bytes) -> None:
        if not content.startswith(PDF_MAGIC):
            raise AppError(
                "File content is not a valid PDF",
                code="invalid_pdf_content",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    async def _save_file(self, filename: str, content: bytes) -> Path:
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self._upload_dir / f"{uuid4().hex}_{filename}"
        await asyncio.to_thread(stored_path.write_bytes, content)
        return stored_path
