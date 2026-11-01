"""NewsData.io API ingestion module for NewsLens India.

Integrates the NewsData.io Latest News API (https://newsdata.io/api/1/latest)
with secure header authentication (X-ACCESS-KEY), proactive quota governance,
three distinct discovery profiles (india_publishers, global_latest, india_global_coverage),
cycle-safe pagination, and multi-provider provenance tracking.
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import requests

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
from src.ingestion.registry import CANONICAL_NEWSDATA_ID, CANONICAL_NEWSDATA_NAME
from src.models import NormalizedArticle, canonicalize_url

if TYPE_CHECKING:
    from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

NEWSDATA_BASE_URL = "https://newsdata.io/api/1"
NEWSDATA_LATEST_ENDPOINT = f"{NEWSDATA_BASE_URL}/latest"
_DEFAULT_USER_AGENT = "NewsLensIndia/0.1 (Python 3.12; Academic Research)"

# Three Canonical Discovery Profiles
PROFILE_INDIA_PUBLISHERS = "india_publishers"
PROFILE_GLOBAL_LATEST = "global_latest"
PROFILE_INDIA_GLOBAL_COVERAGE = "india_global_coverage"

VALID_DISCOVERY_PROFILES = frozenset(
    {
        PROFILE_INDIA_PUBLISHERS,
        PROFILE_GLOBAL_LATEST,
        PROFILE_INDIA_GLOBAL_COVERAGE,
    }
)

# Mapping of common language names to 2-letter ISO codes
LANGUAGE_MAP = {
    "english": "en",
    "hindi": "hi",
    "bengali": "bn",
    "tamil": "ta",
    "telugu": "te",
    "marathi": "mr",
    "gujarati": "gu",
    "kannada": "kn",
    "malayalam": "ml",
    "punjabi": "pa",
    "urdu": "ur",
}


class NewsDataClient:
    """Production-grade client for NewsData.io with quota governance and multi-profile discovery."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = NEWSDATA_BASE_URL,
        endpoint_url: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        daily_budget: Optional[int] = None,
        rolling_15m_budget: Optional[int] = None,
        min_interval_seconds: Optional[float] = None,
        max_pages_per_run: Optional[int] = None,
        request_timeout: int = 12,
        max_retries: int = 1,
        retry_delay_seconds: float = 1.5,
    ):
        # Resolve credentials securely from argument or environment
        self.api_key = (api_key or os.environ.get("NEWSDATA_API_KEY", "")).strip()
        self.base_url = base_url.rstrip("/")
        self.endpoint_url = endpoint_url or f"{self.base_url}/latest"
        self.db = db

        # Quota and budgeting controls
        self.daily_budget = (
            daily_budget
            if daily_budget is not None
            else int(os.environ.get("NEWSDATA_DAILY_BUDGET", "50"))
        )
        self.rolling_15m_budget = (
            rolling_15m_budget
            if rolling_15m_budget is not None
            else int(os.environ.get("NEWSDATA_15MIN_BUDGET", "10"))
        )
        self.min_interval_seconds = (
            min_interval_seconds
            if min_interval_seconds is not None
            else float(os.environ.get("NEWSDATA_MIN_REFRESH_INTERVAL", "60.0"))
        )
        self.max_pages_per_run = (
            max_pages_per_run
            if max_pages_per_run is not None
            else int(os.environ.get("NEWSDATA_MAX_PAGES", "2"))
        )

        self.request_timeout = request_timeout
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

        self._concurrency_lock = threading.Lock()
        self._last_request_time: float = 0.0

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key)

    def _throttle(self) -> None:
        """Throttles requests to respect minimal interval between network calls."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

    def fetch_profile(
        self,
        profile: str = PROFILE_INDIA_PUBLISHERS,
        query: Optional[str] = None,
        language: Optional[str] = None,
        category: Optional[str] = None,
        max_pages: int = 1,
    ) -> ProviderFetchResult:
        """Executes targeted news discovery for one of the three canonical profiles.

        Profiles:
          - india_publishers: Reporting published by Indian newsrooms (country='in').
          - global_latest: International news without country restriction.
          - india_global_coverage: Global newsrooms reporting on India (q='India').
        """
        start_time = time.perf_counter()
        source_id = CANONICAL_NEWSDATA_ID
        source_name = CANONICAL_NEWSDATA_NAME

        if profile not in VALID_DISCOVERY_PROFILES:
            profile = PROFILE_INDIA_PUBLISHERS

        # Guard: Check configuration
        if not self.is_configured:
            logger.info("NewsData.io key unconfigured. Profile '%s' skipped.", profile)
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="newsdata",
                status=STATUS_DISABLED,
                articles=[],
                items_count=0,
                duration_ms=0.0,
                error_message="NewsData.io API key is not configured (NEWSDATA_API_KEY). Ingestion skipped.",
            )

        # Thread-safe concurrent execution guard
        with self._concurrency_lock:
            # Persistent Quota Governance Check
            if self.db:
                allowed, reason = self.db.check_provider_budget(
                    provider_id=source_id,
                    profile=profile,
                    daily_budget=self.daily_budget,
                    rolling_15m_budget=self.rolling_15m_budget,
                    min_interval_seconds=self.min_interval_seconds,
                )
                if not allowed:
                    logger.warning("NewsData.io quota limit reached for %s: %s", profile, reason)
                    return ProviderFetchResult(
                        source_id=source_id,
                        source_name=source_name,
                        source_type="newsdata",
                        status=STATUS_QUOTA_EXCEEDED,
                        articles=[],
                        items_count=0,
                        duration_ms=(time.perf_counter() - start_time) * 1000,
                        error_message=reason,
                    )

            # Build query parameters per profile
            base_params: Dict[str, Any] = {}

            if profile == PROFILE_INDIA_PUBLISHERS:
                base_params["country"] = "in"
                if language:
                    base_params["language"] = language.strip().lower()
                if query and query.strip():
                    base_params["q"] = query.strip()

            elif profile == PROFILE_GLOBAL_LATEST:
                # Global query behavior: No country='in' restriction
                if language:
                    base_params["language"] = language.strip().lower()
                else:
                    base_params["language"] = "en"
                if query and query.strip():
                    base_params["q"] = query.strip()

            elif profile == PROFILE_INDIA_GLOBAL_COVERAGE:
                # International outlets reporting about India:
                # Exclude domestic Indian newsrooms using NewsData.io's excludecountry parameter
                base_params["excludecountry"] = "in"
                search_term = query.strip() if query and query.strip() else "India"
                base_params["q"] = search_term
                if language:
                    base_params["language"] = language.strip().lower()
                else:
                    base_params["language"] = "en"

            if category and category.strip():
                base_params["category"] = category.strip().lower()

            # Pagination controls
            page_budget = min(max(max_pages, 1), self.max_pages_per_run)
            collected_articles: List[NormalizedArticle] = []
            seen_tokens: Set[str] = set()
            next_page_token: Optional[str] = None
            last_http_code: Optional[int] = None
            fatal_error_result: Optional[ProviderFetchResult] = None

            for page_idx in range(page_budget):
                reservation_id: Optional[int] = None
                if self.db:
                    # Multi-worker atomic budget reservation
                    # Only enforce min_interval on page 0 so multi-page pagination within same cycle isn't blocked
                    check_interval = self.min_interval_seconds if page_idx == 0 else 0.0
                    allowed, reason, reservation_id = self.db.reserve_provider_budget(
                        provider_id=source_id,
                        profile=profile,
                        daily_budget=self.daily_budget,
                        rolling_15m_budget=self.rolling_15m_budget,
                        min_interval_seconds=check_interval,
                        credits=1,
                    )
                    if not allowed:
                        logger.warning(
                            "NewsData.io quota limit reached for %s (page %d): %s",
                            profile,
                            page_idx,
                            reason,
                        )
                        if not collected_articles:
                            return ProviderFetchResult(
                                source_id=source_id,
                                source_name=source_name,
                                source_type="newsdata",
                                status=STATUS_QUOTA_EXCEEDED,
                                articles=[],
                                items_count=0,
                                duration_ms=(time.perf_counter() - start_time) * 1000,
                                error_message=reason,
                            )
                        # If subsequent page is blocked by quota, break and return already collected articles
                        break

                params = dict(base_params)
                if next_page_token:
                    params["page"] = next_page_token

                dispatched = False
                page_fetch_start = time.perf_counter()
                try:
                    dispatched = True
                    page_res = self._execute_request(params)
                except Exception as exc:
                    req_latency = (time.perf_counter() - page_fetch_start) * 1000
                    if self.db and reservation_id is not None:
                        # Conservative accounting: Once dispatched, treat ambiguous outcomes as potentially consumed
                        self.db.finalize_provider_request(
                            reservation_id=reservation_id,
                            status_code=None,
                            outcome=STATUS_PROVIDER_UNAVAILABLE,
                            latency_ms=req_latency,
                            credits_consumed=1 if dispatched else 0,
                        )
                    raise exc

                req_latency = (time.perf_counter() - page_fetch_start) * 1000
                outcome = page_res.get("status", "unknown")
                http_status = page_res.get("http_status")
                # Conservative accounting: any dispatched HTTP request (including timeouts, rate-limits,
                # provider errors) is conservatively treated as consumed (1 credit). Only pre-dispatch cancel is 0.
                credits = 1

                # Finalize request reservation
                if self.db and reservation_id is not None:
                    self.db.finalize_provider_request(
                        reservation_id=reservation_id,
                        status_code=http_status,
                        outcome=outcome,
                        latency_ms=req_latency,
                        credits_consumed=credits,
                    )

                if page_res.get("status") != STATUS_SUCCESS:
                    # If first page failed, return fatal error result
                    if not collected_articles:
                        fatal_error_result = ProviderFetchResult(
                            source_id=source_id,
                            source_name=source_name,
                            source_type="newsdata",
                            status=page_res.get("status", STATUS_PROVIDER_UNAVAILABLE),
                            articles=[],
                            items_count=0,
                            duration_ms=(time.perf_counter() - start_time) * 1000,
                            http_status=page_res.get("http_status"),
                            error_message=page_res.get("error_message"),
                        )
                        break
                    # Otherwise stop paging on subsequent page failure
                    break

                last_http_code = page_res.get("http_status", 200)
                raw_items = page_res.get("raw_items", [])
                token_returned = page_res.get("nextPage")

                # Normalize raw items into domain articles
                articles_on_page = self._normalize_items(
                    raw_items=raw_items,
                    discovery_profile=profile,
                    query_used=params.get("q", ""),
                )
                collected_articles.extend(articles_on_page)

                # Pagination termination checks
                if not token_returned or not str(token_returned).strip():
                    break
                token_str = str(token_returned).strip()
                if token_str in seen_tokens:
                    logger.warning(
                        "Repeated pagination token detected (%s); breaking loop.", token_str
                    )
                    break
                seen_tokens.add(token_str)
                next_page_token = token_str

            if fatal_error_result:
                return fatal_error_result

            total_duration = (time.perf_counter() - start_time) * 1000
            final_status = STATUS_SUCCESS if collected_articles else STATUS_NO_RESULTS

            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="newsdata",
                status=final_status,
                articles=collected_articles,
                items_count=len(collected_articles),
                duration_ms=total_duration,
                http_status=last_http_code or 200,
            )

    def fetch_articles(
        self,
        query: Optional[str] = None,
        country: Optional[str] = "in",
        language: Optional[str] = "en",
        category: Optional[str] = None,
        page: Optional[str] = None,
    ) -> ProviderFetchResult:
        """Backward-compatible fetch adhering to standard Provider protocol."""
        # Map parameters to appropriate profile
        if country and country.lower() == "in":
            profile = PROFILE_INDIA_PUBLISHERS
        elif query and "india" in query.lower() and not country:
            profile = PROFILE_INDIA_GLOBAL_COVERAGE
        else:
            profile = PROFILE_GLOBAL_LATEST

        return self.fetch_profile(
            profile=profile,
            query=query,
            language=language,
            category=category,
            max_pages=1,
        )

    def _execute_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single HTTP GET request against NewsData.io with secure headers."""
        headers = {
            "X-ACCESS-KEY": self.api_key,
            "User-Agent": _DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }

        resp: Optional[requests.Response] = None
        last_error_msg: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                self._last_request_time = time.time()
                resp = requests.get(
                    self.endpoint_url,
                    params=params,
                    headers=headers,
                    timeout=self.request_timeout,
                )
                break
            except requests.exceptions.Timeout as e:
                last_error_msg = f"NewsData.io timeout: {e}"
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
                else:
                    return {
                        "status": STATUS_TIMEOUT,
                        "error_message": "NewsData.io connection timed out.",
                    }
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                last_error_msg = f"NewsData.io connection error: {e}"
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
                else:
                    return {
                        "status": STATUS_PROVIDER_UNAVAILABLE,
                        "error_message": "NewsData.io endpoint unreachable.",
                    }
            except Exception as e:
                return {
                    "status": STATUS_PROVIDER_UNAVAILABLE,
                    "error_message": f"Unexpected error: {e}",
                }

        if resp is None:
            return {
                "status": STATUS_PROVIDER_UNAVAILABLE,
                "error_message": last_error_msg or "Failed to connect to NewsData.io.",
            }

        code = resp.status_code

        if code == 429:
            return {
                "status": STATUS_RATE_LIMITED,
                "http_status": 429,
                "error_message": "NewsData.io rate limit reached (HTTP 429). Please wait before retrying.",
            }
        if code in (401, 403):
            return {
                "status": STATUS_PROVIDER_UNAVAILABLE,
                "http_status": code,
                "error_message": f"NewsData.io authentication failed (HTTP {code}). Check NEWSDATA_API_KEY.",
            }
        if code != 200:
            return {
                "status": STATUS_PROVIDER_UNAVAILABLE,
                "http_status": code,
                "error_message": f"NewsData.io returned HTTP {code}.",
            }

        try:
            data = resp.json()
        except Exception:
            return {
                "status": STATUS_INVALID_RESPONSE,
                "http_status": code,
                "error_message": "NewsData.io response was not valid JSON.",
            }

        if not isinstance(data, dict):
            return {
                "status": STATUS_INVALID_RESPONSE,
                "http_status": code,
                "error_message": "NewsData.io response body was not a JSON object.",
            }

        api_status = data.get("status")
        if api_status == "error":
            error_data = data.get("results", {})
            err_msg = (
                error_data.get("message") if isinstance(error_data, dict) else str(error_data)
            ) or "API returned error status."
            err_code = error_data.get("code") if isinstance(error_data, dict) else ""
            status_cls = (
                STATUS_RATE_LIMITED if "RateLimit" in str(err_code) else STATUS_PROVIDER_UNAVAILABLE
            )
            return {
                "status": status_cls,
                "http_status": code,
                "error_message": f"NewsData.io error: {err_msg}",
            }

        raw_results = data.get("results")
        if not isinstance(raw_results, list) or len(raw_results) == 0:
            return {
                "status": STATUS_NO_RESULTS,
                "http_status": code,
                "raw_items": [],
                "nextPage": data.get("nextPage"),
            }

        return {
            "status": STATUS_SUCCESS,
            "http_status": code,
            "raw_items": raw_results,
            "nextPage": data.get("nextPage"),
        }

    def _normalize_items(
        self,
        raw_items: List[Dict[str, Any]],
        discovery_profile: str,
        query_used: str,
    ) -> List[NormalizedArticle]:
        """Normalizes NewsData.io items with strict metadata separation."""
        now_iso = datetime.now(timezone.utc).isoformat()
        normalized: List[NormalizedArticle] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            raw_link = (item.get("link") or "").strip()
            clean_url = canonicalize_url(raw_link) if raw_link else ""
            title = (item.get("title") or "").strip()

            if not title and not clean_url:
                continue

            # Deterministic ID derivation: SHA-256 of canonical URL
            if clean_url:
                art_id = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]
            elif item.get("article_id"):
                art_id = hashlib.sha256(str(item["article_id"]).encode("utf-8")).hexdigest()[:16]
            else:
                art_id = hashlib.sha256(title.encode("utf-8")).hexdigest()[:16]

            # Actual publisher name
            publisher = (
                item.get("source_name")
                or item.get("source_id")
                or (clean_url.split("//")[-1].split("/")[0] if clean_url else "NewsData Publisher")
            ).strip()

            pub_date = item.get("pubDate") or ""

            # Publisher country: Country where newsroom is based
            raw_country = item.get("country")
            if isinstance(raw_country, list) and raw_country:
                publisher_country = str(raw_country[0]).upper()
            elif isinstance(raw_country, str) and raw_country.strip():
                publisher_country = raw_country.strip().upper()
            elif discovery_profile == PROFILE_INDIA_PUBLISHERS:
                publisher_country = "IN"
            else:
                publisher_country = None  # Explicitly unknown, do NOT fabricate 'GLOBAL' or 'INTL'

            # Query discovery semantics (context of the API request, NOT the article content)
            if discovery_profile == PROFILE_INDIA_PUBLISHERS:
                discovery_scope = "domestic_publishers"
                discovery_subject = "india_domestic"
            elif discovery_profile == PROFILE_INDIA_GLOBAL_COVERAGE:
                discovery_scope = "international_on_india"
                discovery_subject = "india_search"
            else:
                discovery_scope = "global_discovery"
                discovery_subject = "general"

            # Language normalization
            raw_lang = item.get("language")
            if isinstance(raw_lang, list) and raw_lang:
                lang_str = str(raw_lang[0]).lower()
            elif isinstance(raw_lang, str) and raw_lang:
                lang_str = raw_lang.strip().lower()
            else:
                lang_str = "en"
            lang_code = LANGUAGE_MAP.get(lang_str, lang_str[:2] if len(lang_str) >= 2 else "en")

            # Description / content summary
            summary_text = (item.get("description") or "").strip()
            if not summary_text and item.get("content"):
                summary_text = str(item["content"]).strip()[:400]

            # Detailed metadata preservation
            metadata: Dict[str, Any] = {
                "article_id": item.get("article_id"),
                "source_id": item.get("source_id"),
                "source_priority": item.get("source_priority"),
                "category": item.get("category"),
                "creator": item.get("creator"),
                "keywords": item.get("keywords"),
                "image_url": item.get("image_url"),
                "discovery_profile": discovery_profile,
                "discovery_scope": discovery_scope,
                "discovery_subject": discovery_subject,
                "publisher_country": publisher_country,
                "story_geography": None,  # Story geography is unknown unless extracted/corroborated
            }

            normalized.append(
                NormalizedArticle(
                    id=art_id,
                    title=title or "Untitled",
                    url=clean_url,
                    publisher=publisher,
                    published_at=pub_date,
                    ingested_at=now_iso,
                    source_type="newsdata",
                    summary=summary_text,
                    language=lang_code,
                    country=publisher_country,
                    query=query_used,
                    raw_metadata=metadata,
                    origin="newsdata",
                )
            )

        return normalized

    def test_upstream_connectivity(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Safely verifies live upstream API authentication without ever logging or leaking the secret."""
        key = (api_key or self.api_key).strip()
        if not key:
            return {
                "status": "BLOCKED",
                "message": "Live API verification is blocked: NEWSDATA_API_KEY is not configured.",
                "authenticated": False,
            }

        headers = {
            "X-ACCESS-KEY": key,
            "User-Agent": _DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        params = {"country": "in", "size": 1}

        try:
            start = time.perf_counter()
            resp = requests.get(
                self.endpoint_url,
                params=params,
                headers=headers,
                timeout=8,
            )
            lat = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    return {
                        "status": "SUCCESS",
                        "authenticated": True,
                        "latency_ms": round(lat, 1),
                        "total_results": data.get("totalResults", 0),
                        "endpoint": self.endpoint_url,
                    }
                return {
                    "status": "FAILED",
                    "authenticated": False,
                    "http_status": 200,
                    "api_error": data.get("results"),
                }
            elif resp.status_code in (401, 403):
                return {
                    "status": "UNAUTHORIZED",
                    "authenticated": False,
                    "http_status": resp.status_code,
                    "message": "Invalid API key or insufficient permissions.",
                }
            elif resp.status_code == 429:
                return {
                    "status": "RATE_LIMITED",
                    "authenticated": True,
                    "http_status": 429,
                    "message": "Rate limit exceeded on authenticated account.",
                }
            return {
                "status": "ERROR",
                "authenticated": False,
                "http_status": resp.status_code,
            }
        except Exception as e:
            return {
                "status": "UNREACHABLE",
                "authenticated": False,
                "error": type(e).__name__,
            }
