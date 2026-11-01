"""Pydantic schemas for Ingestion operations and triggers."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestionRefreshRequest(BaseModel):
    source_type: Optional[str] = Field("rss", pattern="^(rss|gdelt|newsdata|all)$")
    profile: Optional[str] = Field(
        "india_publishers",
        pattern="^(india_publishers|global_latest|india_global_coverage|all)$",
    )
    max_pages: Optional[int] = Field(1, ge=1, le=5)


class IngestionStatusResponse(BaseModel):
    is_syncing: bool
    last_sync_timestamp: Optional[str]
    total_articles: int
    source_statuses: list[dict]
    quota: Optional[Dict[str, Any]] = None
    supported_profiles: List[str] = [
        "india_publishers",
        "global_latest",
        "india_global_coverage",
    ]


class IngestionRefreshResponse(BaseModel):
    success: bool
    total_fetched: int
    new_stored: int
    duration_ms: float
    all_succeeded: bool
    all_failed: bool
    summary: Dict[str, str]
    discovery_profile: Optional[str] = None
    quota_telemetry: Optional[Dict[str, Any]] = None
