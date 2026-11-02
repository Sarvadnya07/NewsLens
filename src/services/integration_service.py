"""Central API Integration Management Service for NewsLens India.

Coordinates health checks, credential presence, status reporting, quota telemetry,
and on-demand refresh across all news providers, aggregators, and evidence APIs.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.config import settings
from src.ingestion.currents import CurrentsClient
from src.ingestion.factcheck import GoogleFactCheckClient
from src.ingestion.gdelt import GdeltClient
from src.ingestion.guardian import GuardianClient
from src.ingestion.models import (
    STATUS_INVALID_RESPONSE,
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
)
from src.ingestion.newsdata import NewsDataClient
from src.ingestion.registry import (
    CANONICAL_CURRENTS_ID,
    CANONICAL_FACTCHECK_ID,
    CANONICAL_GDELT_ID,
    CANONICAL_GUARDIAN_ID,
    CANONICAL_NEWSDATA_ID,
    PROVIDER_REGISTRY,
    ProviderDescriptor,
)
from src.ingestion.rss import RssIngestionService
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class IntegrationManager:
    """Orchestrates configuration inspection, connectivity tests, and provider refreshes."""

    def __init__(
        self,
        db: DatabaseManager,
        rss: Optional[RssIngestionService] = None,
        gdelt: Optional[GdeltClient] = None,
        newsdata: Optional[NewsDataClient] = None,
        currents: Optional[CurrentsClient] = None,
        guardian: Optional[GuardianClient] = None,
        factcheck: Optional[GoogleFactCheckClient] = None,
    ):
        self.db = db
        self.rss = rss or RssIngestionService()
        self.gdelt = gdelt or GdeltClient()
        self.newsdata = newsdata or NewsDataClient(db=self.db)
        self.currents = currents or CurrentsClient(db=self.db)
        self.guardian = guardian or GuardianClient(db=self.db)
        self.factcheck = factcheck or GoogleFactCheckClient(db=self.db)

    def get_provider_status(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Returns comprehensive status telemetry for a single provider."""
        descriptor = PROVIDER_REGISTRY.get(provider_id)
        if not descriptor:
            return None

        # Determine configured and enabled states
        configured, enabled = self._get_provider_state(descriptor)

        # Retrieve database telemetry
        db_status = self.db.get_source_status(descriptor.name) or {}

        # Canonical quota DTO (None when NewsLens manages no budget for this provider)
        quota = self._quota_shape(provider_id)

        # A historical success must not keep a provider "operational" forever.
        last_evidence_at = db_status.get("last_attempt_at") or db_status.get("last_refresh_at")
        evidence_is_fresh = self._evidence_is_fresh(last_evidence_at)

        # Status badge logic
        status_label = "not_configured"
        if not descriptor.is_active:
            status_label = (
                "retired"
                if "retired" in descriptor.category.lower() or "deccan" in descriptor.id
                else "backlog"
            )
        elif not enabled:
            status_label = "disabled"
        elif not configured and descriptor.requires_api_key:
            status_label = "not_configured"
        elif descriptor.requires_api_key and configured:
            # Check if live authenticated test succeeded
            last_status = db_status.get("last_attempt_status") or db_status.get("status")
            if last_status == STATUS_SUCCESS:
                status_label = "operational" if evidence_is_fresh else "degraded"
            elif last_status == STATUS_RATE_LIMITED:
                status_label = "rate_limited"
            elif last_status in (
                STATUS_PROVIDER_UNAVAILABLE,
                STATUS_TIMEOUT,
                STATUS_INVALID_RESPONSE,
            ):
                status_label = "provider_error"
            else:
                status_label = "configured_not_tested"
        else:
            # Open/no-key feeds (RSS and GDELT)
            last_status = db_status.get("last_attempt_status") or db_status.get("status")
            if last_status == STATUS_SUCCESS:
                status_label = "operational" if evidence_is_fresh else "degraded"
            elif last_status == STATUS_RATE_LIMITED:
                status_label = "rate_limited"
            elif last_status in (
                STATUS_PROVIDER_UNAVAILABLE,
                STATUS_TIMEOUT,
                STATUS_INVALID_RESPONSE,
            ):
                status_label = "provider_error"
            else:
                # No attempt evidence: being reachable by design is not proof of health.
                status_label = "configured_not_tested"

        return {
            "id": descriptor.id,
            "name": descriptor.name,
            "category": descriptor.category,
            "source_type": descriptor.source_type,
            "domain": descriptor.domain,
            "is_active": descriptor.is_active,
            "requires_api_key": descriptor.requires_api_key,
            "env_key_name": descriptor.env_key_name,
            "is_configured": configured,
            "is_enabled": enabled,
            "status_label": status_label,
            "last_refresh_at": db_status.get("last_refresh_at"),
            "last_attempt_at": db_status.get("last_attempt_at"),
            "last_attempt_status": db_status.get("last_attempt_status"),
            "last_http_status": db_status.get("last_http_status"),
            "last_latency_ms": db_status.get("last_latency_ms"),
            "items_count": db_status.get("items_fetched", 0),
            "new_items_inserted": db_status.get("new_items_inserted", 0),
            "error_message": db_status.get("error_message"),
            "quota": quota,
            "supported_profiles": list(descriptor.supported_profiles),
            "documentation_url": descriptor.documentation_url,
            "terms_url": descriptor.terms_url,
        }

    def get_all_provider_statuses(self) -> List[Dict[str, Any]]:
        """Returns current operational status for all registered providers."""
        statuses = (self.get_provider_status(pid) for pid in PROVIDER_REGISTRY if pid)
        return [status for status in statuses if status is not None]

    def test_provider_connection(self, provider_id: str) -> Dict[str, Any]:
        """Performs a safe, bounded connection test for the requested provider."""
        descriptor = PROVIDER_REGISTRY.get(provider_id)
        if not descriptor:
            return {
                "provider_id": provider_id,
                "success": False,
                "status": "not_found",
                "message": f"Provider '{provider_id}' is not registered.",
            }

        if provider_id == CANONICAL_NEWSDATA_ID:
            res = self._newsdata_connection_test()
        elif provider_id == CANONICAL_CURRENTS_ID:
            res = self.currents.test_connection()
        elif provider_id == CANONICAL_GUARDIAN_ID:
            res = self.guardian.test_connection()
        elif provider_id == CANONICAL_FACTCHECK_ID:
            res = self.factcheck.test_connection()
        elif provider_id == CANONICAL_GDELT_ID:
            start = time.perf_counter()
            fetch_res = self.gdelt.fetch_articles(keyword="India", max_records=1)
            duration_ms = (time.perf_counter() - start) * 1000
            res = {
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": "connected" if fetch_res.status == STATUS_SUCCESS else fetch_res.status,
                "message": fetch_res.error_message or "GDELT API is reachable.",
                "http_status": fetch_res.http_status,
                "latency_ms": duration_ms,
            }
        elif descriptor.source_type == "rss":
            start = time.perf_counter()
            fetch_res = self.rss.fetch_feed_result(descriptor.name, descriptor.endpoint_url)
            duration_ms = (time.perf_counter() - start) * 1000
            res = {
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": "connected" if fetch_res.status == STATUS_SUCCESS else fetch_res.status,
                "message": fetch_res.error_message or f"RSS feed '{descriptor.name}' is online.",
                "http_status": fetch_res.http_status,
                "latency_ms": duration_ms,
            }
        else:
            res = {
                "success": False,
                "status": "unsupported",
                "message": f"Connection testing is not supported for '{provider_id}'.",
            }

        res["provider_id"] = provider_id
        return res

    def _newsdata_connection_test(self) -> Dict[str, Any]:
        """NewsData connectivity uses the client's built-in safe diagnostic."""
        diag = self.newsdata.test_upstream_connectivity()
        return {
            "success": bool(diag.get("authenticated")),
            "status": str(diag.get("status", "unknown") or "unknown"),
            "message": str(
                diag.get("message") or diag.get("error") or "NewsData.io connection test completed."
            ),
            "http_status": diag.get("http_status"),
            "latency_ms": diag.get("latency_ms"),
        }

    def refresh_provider(
        self,
        provider_id: str,
        profile: Optional[str] = None,
        query: Optional[str] = None,
        max_pages: int = 1,
    ) -> Dict[str, Any]:
        """Triggers an explicit fetch operation for the specified provider."""
        descriptor = PROVIDER_REGISTRY.get(provider_id)
        if not descriptor:
            return {
                "provider_id": provider_id,
                "success": False,
                "status": "not_found",
                "message": f"Unknown provider '{provider_id}'.",
                "items_fetched": 0,
                "new_stored": 0,
                "duration_ms": 0.0,
                "error_message": f"Unknown provider '{provider_id}'.",
            }

        start = time.perf_counter()

        if provider_id == CANONICAL_NEWSDATA_ID:
            used_prof = profile or "india_publishers"
            fetch_res = self.newsdata.fetch_profile(
                profile=used_prof, query=query, max_pages=max_pages
            )
            inserted = self.db.upsert_articles(fetch_res.articles) if fetch_res.articles else 0
            fetch_res.new_items_inserted = inserted
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="newsdata",
                status=fetch_res.status,
                items_fetched=fetch_res.items_count,
                error_message=fetch_res.error_message,
                http_status=fetch_res.http_status,
                latency_ms=fetch_res.duration_ms,
                new_items_inserted=inserted,
                is_active=1 if self.newsdata.is_configured else 0,
            )
            return {
                "provider_id": provider_id,
                "profile": used_prof,
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": fetch_res.status,
                "items_fetched": fetch_res.items_count,
                "new_stored": inserted,
                "duration_ms": fetch_res.duration_ms,
                "error_message": fetch_res.error_message,
            }

        elif provider_id == CANONICAL_CURRENTS_ID:
            used_prof = profile or "currents_india"
            fetch_res = self.currents.fetch_profile(
                profile=used_prof, query=query, max_pages=max_pages
            )
            inserted = self.db.upsert_articles(fetch_res.articles) if fetch_res.articles else 0
            fetch_res.new_items_inserted = inserted
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="currents",
                status=fetch_res.status,
                items_fetched=fetch_res.items_count,
                error_message=fetch_res.error_message,
                http_status=fetch_res.http_status,
                latency_ms=fetch_res.duration_ms,
                new_items_inserted=inserted,
                is_active=1 if self.currents.is_configured else 0,
            )
            return {
                "provider_id": provider_id,
                "profile": used_prof,
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": fetch_res.status,
                "items_fetched": fetch_res.items_count,
                "new_stored": inserted,
                "duration_ms": fetch_res.duration_ms,
                "error_message": fetch_res.error_message,
            }

        elif provider_id == CANONICAL_GUARDIAN_ID:
            used_prof = profile or "india_coverage"
            fetch_res = self.guardian.fetch_profile(
                profile=used_prof, query=query, max_pages=max_pages
            )
            inserted = self.db.upsert_articles(fetch_res.articles) if fetch_res.articles else 0
            fetch_res.new_items_inserted = inserted
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="guardian",
                status=fetch_res.status,
                items_fetched=fetch_res.items_count,
                error_message=fetch_res.error_message,
                http_status=fetch_res.http_status,
                latency_ms=fetch_res.duration_ms,
                new_items_inserted=inserted,
                is_active=1 if self.guardian.is_configured else 0,
            )
            return {
                "provider_id": provider_id,
                "profile": used_prof,
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": fetch_res.status,
                "items_fetched": fetch_res.items_count,
                "new_stored": inserted,
                "duration_ms": fetch_res.duration_ms,
                "error_message": fetch_res.error_message,
            }

        elif provider_id == CANONICAL_FACTCHECK_ID:
            q = query or "India"
            claims = self.factcheck.search_claims(query=q)
            dur = (time.perf_counter() - start) * 1000
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="factcheck",
                status=STATUS_SUCCESS if claims else STATUS_NO_RESULTS,
                items_fetched=len(claims),
                latency_ms=dur,
                new_items_inserted=len(claims),
                is_active=1 if self.factcheck.is_configured else 0,
            )
            return {
                "provider_id": provider_id,
                "success": True,
                "status": "success",
                "items_fetched": len(claims),
                "new_stored": len(claims),
                "duration_ms": dur,
            }

        elif provider_id == CANONICAL_GDELT_ID:
            fetch_res = self.gdelt.fetch_articles(keyword=query or "India", max_records=25)
            inserted = self.db.upsert_articles(fetch_res.articles) if fetch_res.articles else 0
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="gdelt",
                status=fetch_res.status,
                items_fetched=fetch_res.items_count,
                error_message=fetch_res.error_message,
                http_status=fetch_res.http_status,
                latency_ms=fetch_res.duration_ms,
                new_items_inserted=inserted,
                is_active=1,
            )
            return {
                "provider_id": provider_id,
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": fetch_res.status,
                "items_fetched": fetch_res.items_count,
                "new_stored": inserted,
                "duration_ms": fetch_res.duration_ms,
                "error_message": fetch_res.error_message,
            }

        elif descriptor.source_type == "rss":
            fetch_res = self.rss.fetch_feed_result(descriptor.name, descriptor.endpoint_url)
            inserted = self.db.upsert_articles(fetch_res.articles) if fetch_res.articles else 0
            self.db.record_source_status(
                source_name=descriptor.name,
                source_type="rss",
                status=fetch_res.status,
                items_fetched=fetch_res.items_count,
                error_message=fetch_res.error_message,
                http_status=fetch_res.http_status,
                latency_ms=fetch_res.duration_ms,
                new_items_inserted=inserted,
                is_active=1,
            )
            return {
                "provider_id": provider_id,
                "success": fetch_res.status == STATUS_SUCCESS,
                "status": fetch_res.status,
                "items_fetched": fetch_res.items_count,
                "new_stored": inserted,
                "duration_ms": fetch_res.duration_ms,
                "error_message": fetch_res.error_message,
            }

        return {
            "provider_id": provider_id,
            "success": False,
            "status": "not_implemented",
            "message": f"Refresh not supported for provider '{provider_id}'.",
            "items_fetched": 0,
            "new_stored": 0,
            "duration_ms": 0.0,
            "error_message": f"Refresh is not implemented for provider '{provider_id}'.",
        }

    def _evidence_is_fresh(self, timestamp: Optional[str]) -> bool:
        """True when recorded verification evidence is inside the staleness window."""
        raw = str(timestamp or "").strip()
        if not raw:
            return False
        try:
            observed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return False
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        window = float(getattr(settings, "PROVIDER_STATUS_STALENESS_HOURS", 24.0) or 24.0)
        return datetime.now(timezone.utc) - observed <= timedelta(hours=window)

    def _quota_shape(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Maps the request ledger into the public quota DTO shape.

        Returns ``None`` for providers without a NewsLens-managed request budget
        so the API reports ``quota_supported: false`` instead of fabricated zeros.
        """
        if provider_id == CANONICAL_NEWSDATA_ID:
            raw = self.db.get_provider_quota_telemetry(
                provider_id=CANONICAL_NEWSDATA_ID,
                daily_budget=self.newsdata.daily_budget,
                rolling_15m_budget=self.newsdata.rolling_15m_budget,
            )
        elif provider_id == CANONICAL_CURRENTS_ID:
            raw = self.db.get_provider_quota_telemetry(
                provider_id=CANONICAL_CURRENTS_ID,
                daily_budget=self.currents.daily_budget,
                rolling_15m_budget=self.currents.rolling_15m_budget,
            )
        elif provider_id == CANONICAL_GUARDIAN_ID:
            raw = self.db.get_provider_quota_telemetry(
                provider_id=CANONICAL_GUARDIAN_ID,
                daily_budget=self.guardian.daily_budget,
                rolling_15m_budget=self.guardian.rolling_15m_budget,
            )
        else:
            return None

        limit = int(raw.get("daily_requests_budget") or 0)
        used = int(raw.get("daily_requests_used") or 0)
        return {
            "provider_id": provider_id,
            "quota_supported": True,
            "limit": limit,
            "used": used,
            "remaining": max(limit - used, 0),
            "window": "daily",
            "reset_at": None,
            "unit": "requests",
            "source": "newslens_request_budget",
            "rolling_15m_used": int(raw.get("rolling_15m_used") or 0),
            "rolling_15m_limit": int(raw.get("rolling_15m_budget") or 0),
            "is_exhausted": bool(raw.get("is_exhausted")),
            "last_request_at": raw.get("last_request_at"),
            "last_outcome": raw.get("last_outcome"),
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_provider_state(self, descriptor: ProviderDescriptor) -> tuple[bool, bool]:
        """Returns (is_configured, is_enabled) for a provider."""
        if not descriptor.is_active:
            return False, False

        # RSS feeds require no API keys
        if descriptor.source_type == "rss":
            if descriptor.env_enabled_name:
                enabled = getattr(settings, descriptor.env_enabled_name, True)
                return True, bool(enabled)
            return True, True

        # GDELT requires no API key
        if descriptor.id == CANONICAL_GDELT_ID:
            return True, bool(settings.GDELT_ENABLED)

        # NewsData.io
        if descriptor.id == CANONICAL_NEWSDATA_ID:
            cfg = bool(settings.NEWSDATA_API_KEY and str(settings.NEWSDATA_API_KEY).strip())
            return cfg, bool(settings.NEWSDATA_ENABLED and cfg)

        # Currents
        if descriptor.id == CANONICAL_CURRENTS_ID:
            cfg = bool(settings.CURRENTS_API_KEY and str(settings.CURRENTS_API_KEY).strip())
            return cfg, bool(settings.CURRENTS_ENABLED and cfg)

        # The Guardian
        if descriptor.id == CANONICAL_GUARDIAN_ID:
            cfg = bool(settings.GUARDIAN_API_KEY and str(settings.GUARDIAN_API_KEY).strip())
            return cfg, bool(settings.GUARDIAN_ENABLED and cfg)

        # Google Fact Check
        if descriptor.id == CANONICAL_FACTCHECK_ID:
            cfg = bool(
                settings.GOOGLE_FACTCHECK_API_KEY and str(settings.GOOGLE_FACTCHECK_API_KEY).strip()
            )
            return cfg, bool(settings.GOOGLE_FACTCHECK_ENABLED and cfg)

        # Backlog providers
        if descriptor.env_key_name:
            val = getattr(settings, descriptor.env_key_name, None)
            cfg = bool(val and str(val).strip())
            en = getattr(settings, descriptor.env_enabled_name or "", False)
            return cfg, bool(en and cfg)

        return False, False
