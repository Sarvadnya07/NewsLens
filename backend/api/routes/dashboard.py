"""Dashboard summary and metrics API routes."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_news_service
from backend.schemas.articles import ArticleResponse
from backend.schemas.common import APIResponse
from backend.schemas.dashboard import DashboardSummary, SourceStatusItem
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=APIResponse[DashboardSummary])
def get_dashboard_summary(service: NewsLensService = Depends(get_news_service)):
    """Computes real operational metrics using database-level SQL aggregations."""
    total_articles = service.db.get_article_count()
    source_statuses_raw = service.get_source_statuses()

    source_statuses = [
        SourceStatusItem(
            source_name=st.get("source_name", "Unknown"),
            source_type=st.get("source_type", "rss"),
            last_status=st.get("status", "unknown"),
            items_fetched=st.get("items_fetched", 0),
            last_fetched_at=st.get("last_refresh_at"),
            error_message=st.get("error_message"),
        )
        for st in source_statuses_raw
    ]

    # Only currently active feeds count (retired feeds like Deccan Herald have is_active=0)
    active_sources_count = sum(
        1
        for st in source_statuses_raw
        if st.get("status") == "success" and st.get("is_active", 1) == 1
    )
    total_configured_sources = (
        sum(1 for st in source_statuses_raw if st.get("is_active", 1) == 1) or 7
    )

    recent_raw = service.get_recent_articles(limit=10)
    recent_articles = [
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
            country=a.country or "IN",
            query=a.query or "",
        )
        for a in recent_raw
    ]

    # Database-level SQL aggregations:
    # 1. Ingestion-origin distribution (counts by ingestion pipe: rss, gdelt, manual, unknown)
    # 2. Publisher distribution (counts by actual news outlet/domain)
    sources_dist = service.db.get_sources_distribution()
    publishers_dist = service.db.get_publishers_distribution(limit=10)

    # Coverage clusters count using cached clustering to prevent polling lag
    clusters = service.get_cached_coverage_clusters(sample_limit=50)
    coverage_clusters_count = len(clusters)

    fact_check_count = len(service.retriever.records)

    summary = DashboardSummary(
        total_articles=total_articles,
        active_sources_count=active_sources_count,
        total_configured_sources=total_configured_sources,
        coverage_clusters_count=coverage_clusters_count,
        fact_check_matches_count=fact_check_count,
        recent_articles=recent_articles,
        source_statuses=source_statuses,
        sources_distribution=sources_dist,
        publishers_distribution=publishers_dist,
    )
    return APIResponse(data=summary)
