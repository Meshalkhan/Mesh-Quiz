from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class SuccessResponse[T](BaseModel):
    success: bool = True
    data: T
