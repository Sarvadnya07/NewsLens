"""Common Pydantic models for API responses and errors."""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class APIResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT
    message: Optional[str] = None


class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total matching items")
    total_pages: int = Field(..., ge=0, description="Total pages")


class PaginatedResponse(BaseModel, Generic[DataT]):
    items: List[DataT]
    pagination: PaginationMeta


class APIErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class APIErrorResponse(BaseModel):
    success: bool = False
    error: APIErrorDetail
