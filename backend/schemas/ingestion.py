"""Pydantic schemas for Ingestion operations and triggers."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class IngestionRefreshRequest(BaseModel):
    source_type: Optional[str] = Field("rss", pattern="^(rss|all)$")


class IngestionStatusResponse(BaseModel):
    is_syncing: bool
    last_sync_timestamp: Optional[str]
    total_articles: int
    source_statuses: list[dict]


class IngestionRefreshResponse(BaseModel):
    success: bool
    total_fetched: int
    new_stored: int
    duration_ms: float
    all_succeeded: bool
    all_failed: bool
    summary: Dict[str, str]
