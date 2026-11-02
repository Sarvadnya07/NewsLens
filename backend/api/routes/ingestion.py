"""Ingestion control and synchronization API routes."""

import time
from typing import Iterator

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies import get_news_service
from backend.api.errors import NewsLensAPIException
from backend.config import settings
from backend.schemas.common import APIResponse
from backend.schemas.ingestion import (
    IngestionRefreshRequest,
    IngestionRefreshResponse,
    IngestionStatusResponse,
)
from src.ingestion.models import RefreshResult
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


def _admin_gate(request: Request) -> bool:
    """Delegates to the single centralized authorization policy in backend.main.

    Imported lazily because ``backend.main`` includes this router, so a
    module-level import would be circular.
    """
    from backend.main import verify_admin_access, verify_ingestion_access

    if not bool(getattr(settings, "REQUIRE_ADMIN_AUTH_FOR_INGESTION", False)):
        return True
    if not bool(getattr(settings, "ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV", True)):
        return verify_admin_access(request)
    return verify_ingestion_access(request)


def _refresh_slot() -> Iterator[None]:
    """Rejects a concurrent ingestion refresh instead of stacking provider fan-outs.

    Imported lazily because ``backend.main`` includes this router.
    """
    from backend.main import refresh_coordinator

    key = "ingestion:refresh"
    if not refresh_coordinator.try_start(key):
        raise NewsLensAPIException(
            code="CONFLICT",
            message="A refresh is already running. Wait for it to finish before retrying.",
            status_code=409,
        )
    try:
        yield
    finally:
        refresh_coordinator.finish(key)


@router.get("/status", response_model=APIResponse[IngestionStatusResponse])
def get_ingestion_status(service: NewsLensService = Depends(get_news_service)):
    """Returns current synchronization status, timestamps, and active feeds."""
    statuses = service.get_source_statuses()
    total = service.db.get_article_count()

    last_sync = None
    if statuses:
        dates = [str(s["last_refresh_at"]) for s in statuses if s.get("last_refresh_at")]
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
    request: Request,
    payload: IngestionRefreshRequest = IngestionRefreshRequest.model_validate({}),
    service: NewsLensService = Depends(get_news_service),
    _authorized: bool = Depends(_admin_gate),
    _slot: None = Depends(_refresh_slot),
):
    """Executes live synchronization from verified Indian news feeds.

    Triggers upstream provider requests, so it is gated by the administrative
    policy whenever ``REQUIRE_ADMIN_AUTH_FOR_INGESTION`` is enabled and rate
    limited once enforcement is on. See ``docs/API.md``.
    """
    if bool(getattr(settings, "REQUIRE_ADMIN_AUTH_FOR_INGESTION", False)):
        from backend.main import enforce_rate_limit

        enforce_rate_limit(request, scope="ingestion:refresh")

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
