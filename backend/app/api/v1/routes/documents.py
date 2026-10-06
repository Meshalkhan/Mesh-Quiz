from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.config import Settings, get_settings
from app.schemas.common import SuccessResponse
from app.schemas.document import (
    DocumentDeleteData,
    DocumentListData,
    DocumentUploadData,
)
from app.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get(
    "",
    response_model=SuccessResponse[DocumentListData],
    summary="List indexed documents",
)
async def list_documents(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessResponse[DocumentListData]:
    service = DocumentService(settings)
    return SuccessResponse(data=await service.list_documents())


@router.post(
    "/upload",
    response_model=SuccessResponse[DocumentUploadData],
    summary="Upload a PDF document",
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF file to upload")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessResponse[DocumentUploadData]:
    """Accept a PDF upload, extract text, chunk it, and index embeddings.

    Files are stored temporarily under the configured upload directory.
    Chunks are embedded and persisted in ChromaDB for later retrieval.
    """
    service = DocumentService(settings)
    data = await service.upload_pdf(file)
    return SuccessResponse(data=data)


@router.delete(
    "/{filename}",
    response_model=SuccessResponse[DocumentDeleteData],
    summary="Delete an indexed document",
)
async def delete_document(
    filename: str,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SuccessResponse[DocumentDeleteData]:
    service = DocumentService(settings)
    data = await service.delete_document(unquote(filename))
    return SuccessResponse(data=data)
