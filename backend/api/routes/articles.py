"""Article query, pagination, and manual submission API routes."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from backend.api.dependencies import get_news_service
from backend.api.errors import NewsLensAPIException
from backend.schemas.articles import (
    ArticleDetailResponse,
    ArticleResponse,
    ManualArticleCreate,
)
from backend.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=APIResponse[PaginatedResponse[ArticleResponse]])
def list_articles(
    query: Optional[str] = Query(None, description="Search term for headline"),
    source_type: Optional[str] = Query(None, description="rss, gdelt, newsdata, manual, or all"),
    discovery_profile: Optional[str] = Query(
        None, description="india_publishers, global_latest, or india_global_coverage"
    ),
    sort_order: str = Query("Recency", pattern="^(Recency|Oldest|Chronological)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: NewsLensService = Depends(get_news_service),
):
    """Fetches paginated articles matching filters from real SQLite persistence."""
    offset = (page - 1) * page_size
    res = service.query_monitor_articles(
        query=query,
        source_type=source_type,
        limit=page_size,
        offset=offset,
        sort_order=sort_order,
        discovery_profile=discovery_profile,
    )

    articles = [
        ArticleResponse(
            id=a.id,
            title=a.title,
            url=a.url,
            publisher=a.publisher,
            published_at=a.published_at,
            ingested_at=a.ingested_at,
            source_type=a.source_type,
            summary=a.summary or "",
            language=a.language or "en",
            country=a.country,
            query=a.query or "",
        )
        for a in res["articles"]
    ]

    total_items = res["total_matching"]
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

    return APIResponse(
        data=PaginatedResponse(
            items=articles,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
            ),
        )
    )


@router.get("/{article_id}", response_model=APIResponse[ArticleDetailResponse])
def get_article_detail(
    article_id: str,
    service: NewsLensService = Depends(get_news_service),
):
    """Fetches single article details by ID."""
    art = service.db.get_article_by_id(article_id)
    if not art:
        raise NewsLensAPIException(
            code="ARTICLE_NOT_FOUND",
            message=f"Article with id '{article_id}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return APIResponse(
        data=ArticleDetailResponse(
            id=art.id,
            title=art.title,
            url=art.url,
            publisher=art.publisher,
            published_at=art.published_at,
            ingested_at=art.ingested_at,
            source_type=art.source_type,
            summary=art.summary or "",
            language=art.language or "en",
            country=art.country or "IN",
            query=art.query or "",
        )
    )


@router.post("", response_model=APIResponse[ArticleResponse], status_code=status.HTTP_201_CREATED)
def submit_manual_article(
    payload: ManualArticleCreate,
    service: NewsLensService = Depends(get_news_service),
):
    """Submits a user-provided article for screening and tracking."""
    art = service.submit_manual_article(
        title=payload.title,
        publisher=payload.publisher or "Manual User Submission",
        url=payload.url or "",
        summary=payload.summary or "",
    )
    return APIResponse(
        data=ArticleResponse(
            id=art.id,
            title=art.title,
            url=art.url,
            publisher=art.publisher,
            published_at=art.published_at,
            ingested_at=art.ingested_at,
            source_type=art.source_type,
            summary=art.summary or "",
            language=art.language,
            country=art.country,
            query=art.query,
        ),
        message="Article submitted successfully.",
    )
