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
from src.ingestion.models import RefreshResult
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get("/status", response_model=APIResponse[IngestionStatusResponse])
def get_ingestion_status(service: NewsLensService = Depends(get_news_service)):
    """Returns current synchronization status, timestamps, and active feeds."""
    statuses = service.get_source_statuses()
    total = service.db.get_article_count()

    last_sync = None
    if statuses:
        dates = [s.get("last_refresh_at") for s in statuses if s.get("last_refresh_at")]
        if dates:
            last_sync = max(dates)

    quota_data = service.get_newsdata_quota()
    return APIResponse(
        data=IngestionStatusResponse(
            is_syncing=False,
            last_sync_timestamp=last_sync,
            total_articles=total,
            source_statuses=statuses,
            quota=quota_data,
        )
    )


@router.post("/refresh", response_model=APIResponse[IngestionRefreshResponse])
def trigger_refresh(
    payload: IngestionRefreshRequest = IngestionRefreshRequest(),
    service: NewsLensService = Depends(get_news_service),
):
    """Executes live synchronization from verified Indian news feeds."""
    start = time.perf_counter()
    req_type = (payload.source_type or "rss").strip().lower()
    profile_used = payload.profile or "india_publishers"

    if req_type == "all":
        refresh_res = service.refresh_all()
    elif req_type == "gdelt":
        gdelt_res = service.refresh_gdelt()
        refresh_res = RefreshResult(
            total_fetched=gdelt_res.items_count,
            new_stored=gdelt_res.new_items_inserted,
            duration_ms=gdelt_res.duration_ms,
            provider_results={gdelt_res.source_name: gdelt_res},
            all_succeeded=(gdelt_res.status == "success"),
            all_failed=(gdelt_res.status != "success"),
        )
    elif req_type == "newsdata":
        nd_res = service.refresh_newsdata(
            profile=profile_used,
            max_pages=payload.max_pages or 1,
        )
        refresh_res = RefreshResult(
            total_fetched=nd_res.items_count,
            new_stored=nd_res.new_items_inserted,
            duration_ms=nd_res.duration_ms,
            provider_results={nd_res.source_name: nd_res},
            all_succeeded=(nd_res.status == "success"),
            all_failed=(nd_res.status != "success"),
        )
    else:
        refresh_res = service.refresh_rss_feeds()

    duration = (time.perf_counter() - start) * 1000

    provider_summary = {
        name: f"Status: {res.status}, Count: {res.items_count}"
        for name, res in refresh_res.provider_results.items()
    }

    quota_data = service.get_newsdata_quota() if req_type in ("newsdata", "all") else None

    return APIResponse(
        data=IngestionRefreshResponse(
            success=refresh_res.all_succeeded or (not refresh_res.all_failed),
            total_fetched=refresh_res.total_fetched,
            new_stored=refresh_res.new_stored,
            duration_ms=duration,
            all_succeeded=refresh_res.all_succeeded,
            all_failed=refresh_res.all_failed,
            summary=provider_summary,
            discovery_profile=profile_used if req_type == "newsdata" else None,
            quota_telemetry=quota_data,
        ),
        message=f"Sync completed. Ingested {refresh_res.new_stored} new articles.",
    )
