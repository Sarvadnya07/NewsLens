"""Ingestion control and synchronization API routes."""

import time

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_news_service
from backend.schemas.common import APIResponse
from backend.schemas.ingestion import (
    IngestionRefreshRequest,
    IngestionRefreshResponse,
    IngestionStatusResponse,
)
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/status", response_model=APIResponse[IngestionStatusResponse])
def get_ingestion_status(service: NewsLensService = Depends(get_news_service)):
    """Returns current synchronization status, timestamps, and active feeds."""
    statuses = service.get_source_statuses()
    total = service.db.get_article_count()

    last_sync = None
    if statuses:
        dates = [s.get("last_fetched_at") for s in statuses if s.get("last_fetched_at")]
        if dates:
            last_sync = max(dates)

    return APIResponse(
        data=IngestionStatusResponse(
            is_syncing=False,
            last_sync_timestamp=last_sync,
            total_articles=total,
            source_statuses=statuses,
        )
    )


@router.post("/refresh", response_model=APIResponse[IngestionRefreshResponse])
def trigger_refresh(
    payload: IngestionRefreshRequest = IngestionRefreshRequest(),
    service: NewsLensService = Depends(get_news_service),
):
    """Executes live synchronization from verified Indian news feeds."""
    start = time.perf_counter()
    refresh_res = service.refresh_rss_feeds()
    duration = (time.perf_counter() - start) * 1000

    provider_summary = {
        name: f"Status: {res.status}, Count: {res.items_count}"
        for name, res in refresh_res.provider_results.items()
    }

    return APIResponse(
        data=IngestionRefreshResponse(
            success=refresh_res.all_succeeded or (not refresh_res.all_failed),
            total_fetched=refresh_res.total_fetched,
            new_stored=refresh_res.new_stored,
            duration_ms=duration,
            all_succeeded=refresh_res.all_succeeded,
            all_failed=refresh_res.all_failed,
            summary=provider_summary,
        ),
        message=f"Sync completed. Ingested {refresh_res.new_stored} new articles.",
    )
