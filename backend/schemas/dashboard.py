"""Pydantic schemas for Dashboard summary, telemetry, and source status."""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from backend.schemas.articles import ArticleResponse


class SourceStatusItem(BaseModel):
    source_name: str
    source_type: str
    last_status: str
    items_fetched: int
    last_fetched_at: Optional[str] = None
    error_message: Optional[str] = None


class DashboardSummary(BaseModel):
    total_articles: int
    active_sources_count: int
    total_configured_sources: int
    coverage_clusters_count: int
    fact_check_matches_count: int
    recent_articles: List[ArticleResponse]
    top_stories_limit: int = Field(
        10, description="Configured maximum hard limit for Dashboard Top Stories"
    )
    top_stories_count: int = Field(
        0, description="Actual count of returned Top Stories articles (at most 10)"
    )
    source_statuses: List[SourceStatusItem]
    sources_distribution: Dict[str, int] = Field(
        ...,
        description="Ingestion-origin distribution: counts of articles by source pipe (rss, gdelt, manual, unknown)",
    )
    publishers_distribution: Dict[str, int] = Field(
        ...,
        description="Publisher distribution: counts of articles by news publisher domain or outlet",
    )
