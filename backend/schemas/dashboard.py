"""Pydantic schemas for Dashboard summary, telemetry, and source status."""

from typing import Dict, List, Optional

from pydantic import BaseModel

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
    source_statuses: List[SourceStatusItem]
    sources_distribution: Dict[str, int]
    publishers_distribution: Dict[str, int]
