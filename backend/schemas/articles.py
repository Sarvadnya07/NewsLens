"""Pydantic schemas for Article domain."""

from typing import Optional

from pydantic import BaseModel, Field


class ArticleBase(BaseModel):
    id: str
    title: str
    url: str
    publisher: str
    published_at: str
    source_type: str
    summary: Optional[str] = ""
    language: Optional[str] = "en"
    country: Optional[str] = None
    query: Optional[str] = ""
    image_url: Optional[str] = None


class ArticleResponse(ArticleBase):
    ingested_at: str


class ArticleDetailResponse(ArticleResponse):
    pass


class ManualArticleCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=500, description="Headline or title")
    publisher: Optional[str] = Field("Manual User Submission", max_length=150)
    url: Optional[str] = Field("", max_length=2048)
    summary: Optional[str] = Field("", max_length=5000)


class ArticleFilterParams(BaseModel):
    query: Optional[str] = None
    source_type: Optional[str] = None
    publisher: Optional[str] = None
    page: int = Field(1, ge=1, le=100_000)
    page_size: int = Field(20, ge=1, le=100)
    sort_order: str = Field("Recency", pattern="^(Recency|Oldest|Chronological)$")
