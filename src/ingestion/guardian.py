"""The Guardian Open Platform ingestion client for NewsLens India.

Integrates The Guardian Content API (https://open-platform.theguardian.com) for
first-party global and India-focused journalism.
Developer plan: 500 requests/day, 1 call/second throttle, non-commercial use.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.config import sanitize_text, settings
from src.ingestion.models import (
    STATUS_DISABLED,
    STATUS_INVALID_RESPONSE,
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_QUOTA_EXCEEDED,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ProviderFetchResult,
)
from src.ingestion.registry import CANONICAL_GUARDIAN_ID, CANONICAL_GUARDIAN_NAME
from src.models import NormalizedArticle, canonicalize_url
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

GUARDIAN_API_URL = "https://content.guardianapis.com/search"


class GuardianClient:
    """Client for The Guardian Open Platform API with rate limiting and quota governance."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        request_timeout: float = 20.0,
    ):
        self.api_key = settings.GUARDIAN_API_KEY if api_key is None else api_key
        self.db = db
        self.request_timeout = request_timeout or settings.INTEGRATION_REQUEST_TIMEOUT
        self.daily_budget = settings.GUARDIAN_DAILY_BUDGET
        self.rolling_15m_budget = settings.GUARDIAN_15MIN_BUDGET
        self.min_refresh_interval = settings.GUARDIAN_MIN_REFRESH_INTERVAL

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self.api_key and str(self.api_key).strip())

    @property
    def is_enabled(self) -> bool:
        """Returns True if The Guardian is enabled in settings and configured."""
        return bool(settings.GUARDIAN_ENABLED and self.is_configured)

    def test_connection(self) -> Dict[str, Any]:
        """Performs a minimal bounded authenticated request to verify credentials."""
        if not self.is_configured:
            return {
                "success": False,
                "status": "not_configured",
                "message": "Guardian API key is not configured.",
                "http_status": None,
                "latency_ms": 0.0,
            }

        start = time.perf_counter()
        params: Dict[str, Any] = {
            "api-key": (self.api_key or "").strip(),
            "page-size": 1,
            "show-fields": "headline",
        }

        try:
            resp = requests.get(
                GUARDIAN_API_URL,
                params=params,
                timeout=self.request_timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                if data.get("response", {}).get("status") == "ok":
                    return {
                        "success": True,
                        "status": "connected",
                        "message": "Successfully authenticated with The Guardian Open Platform.",
                        "http_status": 200,
                        "latency_ms": duration_ms,
                    }
                return {
                    "success": False,
                    "status": "invalid_response",
                    "message": "The Guardian API returned non-ok status.",
                    "http_status": 200,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code in (401, 403):
                return {
                    "success": False,
                    "status": "authentication_failed",
                    "message": "Invalid The Guardian API key.",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status": "rate_limited",
                    "message": "The Guardian API quota or throttle exceeded (1 req/sec).",
                    "http_status": 429,
                    "latency_ms": duration_ms,
                }
            else:
                return {
                    "success": False,
                    "status": "provider_unavailable",
                    "message": f"The Guardian API error (HTTP {resp.status_code}).",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status": "timeout",
                "message": "Connection to The Guardian API timed out.",
                "http_status": None,
                "latency_ms": (time.perf_counter() - start) * 1000,
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "message": sanitize_text(str(exc)),
                "http_status": None,
                "latency_ms": (time.perf_counter() - start) * 1000,
            }

    def fetch_profile(
        self,
        profile: str = "india_coverage",
        query: Optional[str] = None,
        max_pages: int = 1,
    ) -> ProviderFetchResult:
        """Fetches latest articles from The Guardian API using selected profile."""
        start_time = time.perf_counter()

        if not self.is_configured:
            return ProviderFetchResult(
                source_id=CANONICAL_GUARDIAN_ID,
                source_name=CANONICAL_GUARDIAN_NAME,
                source_type="guardian",
                status=STATUS_DISABLED,
                articles=[],
                items_count=0,
                duration_ms=0.0,
                error_message="The Guardian API key is not configured.",
            )

        if not settings.GUARDIAN_ENABLED:
            return ProviderFetchResult(
                source_id=CANONICAL_GUARDIAN_ID,
                source_name=CANONICAL_GUARDIAN_NAME,
                source_type="guardian",
                status=STATUS_DISABLED,
                articles=[],
                items_count=0,
                duration_ms=0.0,
                error_message="The Guardian provider is disabled in settings.",
            )

        # Quota reservation check
        reservation_id: Optional[int] = None
        if self.db:
            allowed, reason, reservation_id = self.db.reserve_provider_budget(
                provider_id=CANONICAL_GUARDIAN_ID,
                profile=profile,
                daily_budget=self.daily_budget,
                rolling_15m_budget=self.rolling_15m_budget,
                min_interval_seconds=self.min_refresh_interval,
            )
            if not allowed:
                return ProviderFetchResult(
                    source_id=CANONICAL_GUARDIAN_ID,
                    source_name=CANONICAL_GUARDIAN_NAME,
                    source_type="guardian",
                    status=STATUS_QUOTA_EXCEEDED,
                    articles=[],
                    items_count=0,
                    duration_ms=(time.perf_counter() - start_time) * 1000,
                    error_message=f"The Guardian quota exhausted: {reason}",
                )

        params: Dict[str, Any] = {
            "api-key": (self.api_key or "").strip(),
            "page-size": 20,
            "show-fields": "headline,trailText,byline,standfirst,thumbnail",
            "show-tags": "keyword,contributor",
        }

        if profile == "india_coverage":
            params["q"] = f"India AND ({query.strip()})" if query and query.strip() else "India"
            story_geo = "India"
        else:
            if query and query.strip():
                params["q"] = query.strip()
            params["section"] = "world"
            story_geo = "Global"

        articles: List[NormalizedArticle] = []
        req_dispatched = False

        try:
            req_dispatched = True
            resp = requests.get(
                GUARDIAN_API_URL,
                params=params,
                timeout=self.request_timeout,
            )
            duration = (time.perf_counter() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json().get("response", {})
                results = data.get("results", [])
                for item in results:
                    norm = self._normalize_article(item, profile, story_geo)
                    if norm:
                        articles.append(norm)

                if self.db and reservation_id:
                    self.db.finalize_provider_request(
                        reservation_id=reservation_id,
                        status_code=200,
                        outcome="success" if articles else "no_results",
                        credits_consumed=1,
                        latency_ms=duration,
                    )

                status = STATUS_SUCCESS if articles else STATUS_NO_RESULTS
                return ProviderFetchResult(
                    source_id=CANONICAL_GUARDIAN_ID,
                    source_name=CANONICAL_GUARDIAN_NAME,
                    source_type="guardian",
                    status=status,
                    articles=articles,
                    items_count=len(articles),
                    duration_ms=duration,
                    http_status=200,
                )
            elif resp.status_code == 429:
                if self.db and reservation_id:
                    self.db.finalize_provider_request(
                        reservation_id=reservation_id,
                        status_code=429,
                        outcome="rate_limited",
                        credits_consumed=1,
                        latency_ms=duration,
                    )
                return ProviderFetchResult(
                    source_id=CANONICAL_GUARDIAN_ID,
                    source_name=CANONICAL_GUARDIAN_NAME,
                    source_type="guardian",
                    status=STATUS_RATE_LIMITED,
                    articles=[],
                    items_count=0,
                    duration_ms=duration,
                    error_message="The Guardian rate limit reached (1 call/sec or 500 calls/day).",
                    http_status=429,
                )
            else:
                if self.db and reservation_id:
                    self.db.finalize_provider_request(
                        reservation_id=reservation_id,
                        status_code=resp.status_code,
                        outcome="provider_error",
                        credits_consumed=1,
                        latency_ms=duration,
                    )
                return ProviderFetchResult(
                    source_id=CANONICAL_GUARDIAN_ID,
                    source_name=CANONICAL_GUARDIAN_NAME,
                    source_type="guardian",
                    status=STATUS_PROVIDER_UNAVAILABLE,
                    articles=[],
                    items_count=0,
                    duration_ms=duration,
                    error_message=f"The Guardian API returned HTTP {resp.status_code}",
                    http_status=resp.status_code,
                )
        except requests.exceptions.Timeout:
            dur = (time.perf_counter() - start_time) * 1000
            if self.db and reservation_id:
                self.db.finalize_provider_request(
                    reservation_id=reservation_id,
                    status_code=None,
                    outcome="timeout",
                    credits_consumed=1,
                    latency_ms=dur,
                )
            return ProviderFetchResult(
                source_id=CANONICAL_GUARDIAN_ID,
                source_name=CANONICAL_GUARDIAN_NAME,
                source_type="guardian",
                status=STATUS_TIMEOUT,
                articles=[],
                items_count=0,
                duration_ms=dur,
                error_message="The Guardian API request timed out.",
            )
        except Exception as exc:
            dur = (time.perf_counter() - start_time) * 1000
            if self.db and reservation_id:
                self.db.finalize_provider_request(
                    reservation_id=reservation_id,
                    status_code=None,
                    outcome="error" if req_dispatched else "canceled",
                    credits_consumed=1 if req_dispatched else 0,
                    latency_ms=dur,
                )
            return ProviderFetchResult(
                source_id=CANONICAL_GUARDIAN_ID,
                source_name=CANONICAL_GUARDIAN_NAME,
                source_type="guardian",
                status=STATUS_INVALID_RESPONSE,
                articles=[],
                items_count=0,
                duration_ms=dur,
                error_message=sanitize_text(str(exc)),
            )

    def _normalize_article(
        self, item: Dict[str, Any], profile: str, story_geo: str
    ) -> Optional[NormalizedArticle]:
        url = (item.get("webUrl") or "").strip()
        title = (item.get("webTitle") or "").strip()
        if not url or not title:
            return None

        canonical_url = canonicalize_url(url)
        art_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]

        fields = item.get("fields") or {}
        byline = fields.get("byline")
        publisher = f"The Guardian ({byline})" if byline else "The Guardian"
        summary = (fields.get("trailText") or fields.get("standfirst") or "").strip()
        published_at = item.get("webPublicationDate") or ""

        raw_meta = {
            "guardian_id": item.get("id"),
            "section_id": item.get("sectionId"),
            "section_name": item.get("sectionName"),
            "publisher_domain": "theguardian.com",
            "discovery_profile": profile,
            "story_geography": story_geo,
            "thumbnail": fields.get("thumbnail"),
        }

        return NormalizedArticle(
            id=art_id,
            title=title,
            url=canonical_url,
            publisher=publisher,
            published_at=published_at,
            ingested_at=datetime.now(timezone.utc).isoformat(),
            source_type="guardian",
            origin="guardian",
            summary=summary,
            language="en",
            country="GB",
            query="",
            raw_metadata=raw_meta,
        )
