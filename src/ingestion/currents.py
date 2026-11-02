"""Currents API ingestion client for NewsLens India.

Integrates Currents API (https://currentsapi.services) for international and Indian
news discovery with atomic quota reservations, pagination limits, and source provenance.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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
from src.ingestion.registry import CANONICAL_CURRENTS_ID, CANONICAL_CURRENTS_NAME
from src.models import NormalizedArticle, canonicalize_url
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

CURRENTS_API_URL = "https://api.currentsapi.services/v1/latest-news"


class CurrentsClient:
    """Client for Currents API with atomic quota enforcement and multi-profile support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        request_timeout: float = 20.0,
    ):
        self.api_key = settings.CURRENTS_API_KEY if api_key is None else api_key
        self.db = db
        self.request_timeout = request_timeout or settings.INTEGRATION_REQUEST_TIMEOUT
        self.daily_budget = settings.CURRENTS_DAILY_BUDGET
        self.rolling_15m_budget = settings.CURRENTS_15MIN_BUDGET
        self.min_refresh_interval = settings.CURRENTS_MIN_REFRESH_INTERVAL

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self.api_key and str(self.api_key).strip())

    @property
    def is_enabled(self) -> bool:
        """Returns True if Currents is enabled in settings and configured."""
        return bool(settings.CURRENTS_ENABLED and self.is_configured)

    def test_connection(self) -> Dict[str, Any]:
        """Performs a minimal bounded authenticated request to verify credentials."""
        if not self.is_configured:
            return {
                "success": False,
                "status": "not_configured",
                "message": "Currents API key is not configured.",
                "http_status": None,
                "latency_ms": 0.0,
            }

        start = time.perf_counter()
        headers = {"Authorization": (self.api_key or "").strip()}
        params: Dict[str, Any] = {"language": "en", "page_size": 1}

        try:
            resp = requests.get(
                CURRENTS_API_URL,
                headers=headers,
                params=params,
                timeout=self.request_timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                status_str = data.get("status")
                if status_str == "ok":
                    return {
                        "success": True,
                        "status": "connected",
                        "message": "Successfully authenticated with Currents API.",
                        "http_status": 200,
                        "latency_ms": duration_ms,
                    }
                return {
                    "success": False,
                    "status": "invalid_response",
                    "message": f"Currents API returned non-ok status: {status_str}",
                    "http_status": 200,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code == 401 or resp.status_code == 403:
                return {
                    "success": False,
                    "status": "authentication_failed",
                    "message": "Invalid Currents API key.",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status": "rate_limited",
                    "message": "Currents API quota or rate limit exceeded.",
                    "http_status": 429,
                    "latency_ms": duration_ms,
                }
            else:
                return {
                    "success": False,
                    "status": "provider_unavailable",
                    "message": f"Currents API error (HTTP {resp.status_code}).",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status": "timeout",
                "message": "Connection to Currents API timed out.",
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
        profile: str = "currents_india",
        query: Optional[str] = None,
        language: Optional[str] = "en",
        category: Optional[str] = None,
        max_pages: int = 1,
    ) -> ProviderFetchResult:
        """Fetches latest articles from Currents API for the requested profile."""
        start_time = time.perf_counter()

        if not self.is_configured:
            return ProviderFetchResult(
                source_id=CANONICAL_CURRENTS_ID,
                source_name=CANONICAL_CURRENTS_NAME,
                source_type="currents",
                status=STATUS_DISABLED,
                articles=[],
                items_count=0,
                duration_ms=0.0,
                error_message="Currents API key is not configured.",
                http_status=None,
            )

        if not settings.CURRENTS_ENABLED:
            return ProviderFetchResult(
                source_id=CANONICAL_CURRENTS_ID,
                source_name=CANONICAL_CURRENTS_NAME,
                source_type="currents",
                status=STATUS_DISABLED,
                articles=[],
                items_count=0,
                duration_ms=0.0,
                error_message="Currents provider is disabled in settings.",
                http_status=None,
            )

        # Quota reservation check
        reservation_id: Optional[int] = None
        if self.db:
            allowed, reason, reservation_id = self.db.reserve_provider_budget(
                provider_id=CANONICAL_CURRENTS_ID,
                profile=profile,
                daily_budget=self.daily_budget,
                rolling_15m_budget=self.rolling_15m_budget,
                min_interval_seconds=self.min_refresh_interval,
            )
            if not allowed:
                return ProviderFetchResult(
                    source_id=CANONICAL_CURRENTS_ID,
                    source_name=CANONICAL_CURRENTS_NAME,
                    source_type="currents",
                    status=STATUS_QUOTA_EXCEEDED,
                    articles=[],
                    items_count=0,
                    duration_ms=(time.perf_counter() - start_time) * 1000,
                    error_message=f"Currents quota exhausted: {reason}",
                    http_status=None,
                )

        headers = {"Authorization": (self.api_key or "").strip()}
        params: Dict[str, Any] = {"language": language or "en"}

        if profile == "currents_india":
            params["country"] = "IN"
            story_geo = "India"
        else:
            story_geo = "Global"

        if query and query.strip():
            params["keywords"] = query.strip()
        if category and category.strip():
            params["category"] = category.strip()

        articles: List[NormalizedArticle] = []
        req_dispatched = False

        try:
            req_dispatched = True
            resp = requests.get(
                CURRENTS_API_URL,
                headers=headers,
                params=params,
                timeout=self.request_timeout,
            )
            duration = (time.perf_counter() - start_time) * 1000

            if resp.status_code == 200:
                data = resp.json()
                raw_news = data.get("news", [])
                for item in raw_news:
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
                    source_id=CANONICAL_CURRENTS_ID,
                    source_name=CANONICAL_CURRENTS_NAME,
                    source_type="currents",
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
                    source_id=CANONICAL_CURRENTS_ID,
                    source_name=CANONICAL_CURRENTS_NAME,
                    source_type="currents",
                    status=STATUS_RATE_LIMITED,
                    articles=[],
                    items_count=0,
                    duration_ms=duration,
                    error_message="Currents API rate limit exceeded.",
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
                    source_id=CANONICAL_CURRENTS_ID,
                    source_name=CANONICAL_CURRENTS_NAME,
                    source_type="currents",
                    status=STATUS_PROVIDER_UNAVAILABLE,
                    articles=[],
                    items_count=0,
                    duration_ms=duration,
                    error_message=f"Currents API returned HTTP {resp.status_code}",
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
                source_id=CANONICAL_CURRENTS_ID,
                source_name=CANONICAL_CURRENTS_NAME,
                source_type="currents",
                status=STATUS_TIMEOUT,
                articles=[],
                items_count=0,
                duration_ms=dur,
                error_message="Currents API request timed out.",
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
                source_id=CANONICAL_CURRENTS_ID,
                source_name=CANONICAL_CURRENTS_NAME,
                source_type="currents",
                status=STATUS_INVALID_RESPONSE,
                articles=[],
                items_count=0,
                duration_ms=dur,
                error_message=sanitize_text(str(exc)),
            )

    def _normalize_article(
        self, item: Dict[str, Any], profile: str, story_geo: str
    ) -> Optional[NormalizedArticle]:
        url = (item.get("url") or "").strip()
        title = (item.get("title") or "").strip()
        if not url or not title:
            return None

        canonical_url = canonicalize_url(url)
        art_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]

        pub_domain = ""
        try:
            pub_domain = urlparse(canonical_url).netloc.replace("www.", "")
        except Exception:
            pass

        publisher = (item.get("author") or pub_domain or "Currents Syndicate").strip()
        published_at = item.get("published") or ""
        summary = (item.get("description") or "").strip()
        language = item.get("language") or "en"

        raw_meta = {
            "currents_id": item.get("id"),
            "category": item.get("category"),
            "image": item.get("image"),
            "publisher_domain": pub_domain,
            "discovery_profile": profile,
            "story_geography": story_geo,
        }

        return NormalizedArticle(
            id=art_id,
            title=title,
            url=canonical_url,
            publisher=publisher,
            published_at=published_at,
            ingested_at=datetime.now(timezone.utc).isoformat(),
            source_type="currents",
            origin="currents",
            summary=summary,
            language=language,
            country="IN" if story_geo == "India" else "GLOBAL",
            query="",
            raw_metadata=raw_meta,
        )
