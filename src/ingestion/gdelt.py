"""GDELT 2.0 Doc API ingestion module for NewsLens India.

Designed with robust rate-limiting, error handling, JSON schema validation,
and article normalization conforming to canonical contracts.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.ingestion.models import (
    STATUS_INVALID_RESPONSE,
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ProviderFetchResult,
)
from src.ingestion.registry import CANONICAL_GDELT_ID, CANONICAL_GDELT_NAME
from src.models import NormalizedArticle, canonicalize_url

logger = logging.getLogger(__name__)

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
_USER_AGENT = "NewsLensIndia/0.1 (Python 3.12; Academic Research)"


class GdeltClient:
    """Client for GDELT 2.0 Doc API with rate throttling, retries, and typed failures."""

    def __init__(
        self,
        request_timeout: int = 15,
        min_interval_seconds: float = 5.0,
        max_retries: int = 1,
        retry_delay_seconds: float = 2.0,
    ):
        self.request_timeout = request_timeout
        self.min_interval_seconds = min_interval_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self._last_request_time: float = 0.0

    def _throttle(self) -> None:
        """Enforces at least min_interval_seconds between queries to obey GDELT rate limits."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_interval_seconds:
            sleep_time = self.min_interval_seconds - elapsed
            logger.info("Throttling GDELT request for %.2f seconds", sleep_time)
            time.sleep(sleep_time)

    def search_articles(
        self,
        keyword: str,
        country: Optional[str] = "IN",
        language: Optional[str] = "English",
        timespan: Optional[str] = "24h",
        max_records: int = 30,
    ) -> List[NormalizedArticle]:
        """Backward-compatible helper that searches articles and returns normalized list."""
        result = self.fetch_articles(
            keyword=keyword,
            country=country,
            language=language,
            timespan=timespan,
            max_records=max_records,
        )
        return result.articles

    def fetch_articles(
        self,
        keyword: str,
        country: Optional[str] = "IN",
        language: Optional[str] = "English",
        timespan: Optional[str] = "24h",
        max_records: int = 30,
    ) -> ProviderFetchResult:
        """Executes a structured search against GDELT Doc API and returns a ProviderFetchResult.

        Accurately distinguishes:
          - STATUS_SUCCESS: Articles returned and normalized.
          - STATUS_NO_RESULTS: Genuine 200 response with empty article list.
          - STATUS_RATE_LIMITED: HTTP 429 received.
          - STATUS_TIMEOUT: Network connect/read timeout.
          - STATUS_PROVIDER_UNAVAILABLE: HTTP 5xx or server unreachable.
          - STATUS_INVALID_RESPONSE: Malformed JSON or non-JSON HTML returned.
        """
        start_time = time.perf_counter()
        source_id = CANONICAL_GDELT_ID
        source_name = CANONICAL_GDELT_NAME

        if not keyword or not keyword.strip():
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_NO_RESULTS,
                articles=[],
                items_count=0,
                duration_ms=0.0,
            )

        parts: List[str] = []
        cleaned_kw = keyword.strip()
        if " " in cleaned_kw:
            parts.append(f'"{cleaned_kw}"')
        else:
            parts.append(cleaned_kw)

        if country:
            parts.append(f"sourcecountry:{country}")
        if language:
            parts.append(f"sourcelang:{language}")

        query_str = " ".join(parts)
        params: Dict[str, Any] = {
            "query": query_str,
            "mode": "artlist",
            "format": "json",
            "maxrecords": min(max(max_records, 1), 250),
        }
        if timespan:
            params["timespan"] = timespan

        headers = {"User-Agent": _USER_AGENT}
        resp: Optional[requests.Response] = None
        last_error_msg: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                self._last_request_time = time.time()
                resp = requests.get(
                    GDELT_DOC_ENDPOINT,
                    params=params,
                    headers=headers,
                    timeout=self.request_timeout,
                )
                break
            except requests.exceptions.Timeout as e:
                last_error_msg = f"GDELT connection timed out: {e}"
                if attempt < self.max_retries:
                    logger.warning(
                        "GDELT attempt %d timed out. Retrying in %.1fs...",
                        attempt + 1,
                        self.retry_delay_seconds,
                    )
                    time.sleep(self.retry_delay_seconds)
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return ProviderFetchResult(
                        source_id=source_id,
                        source_name=source_name,
                        source_type="gdelt",
                        status=STATUS_TIMEOUT,
                        articles=[],
                        items_count=0,
                        duration_ms=duration_ms,
                        error_message="GDELT connection timed out.",
                    )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException,
                Exception,
            ) as e:
                last_error_msg = f"GDELT network failure: {e}"
                if attempt < self.max_retries:
                    logger.warning(
                        "GDELT attempt %d failed (%s). Retrying...",
                        attempt + 1,
                        type(e).__name__,
                    )
                    time.sleep(self.retry_delay_seconds)
                else:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    return ProviderFetchResult(
                        source_id=source_id,
                        source_name=source_name,
                        source_type="gdelt",
                        status=STATUS_PROVIDER_UNAVAILABLE,
                        articles=[],
                        items_count=0,
                        duration_ms=duration_ms,
                        error_message="GDELT endpoint unreachable.",
                    )

        duration_ms = (time.perf_counter() - start_time) * 1000

        if resp is None:
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_PROVIDER_UNAVAILABLE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message=last_error_msg or "Failed to connect to GDELT.",
            )

        if resp.status_code == 429:
            logger.warning("GDELT returned 429 Rate Limited for query '%s'", keyword)
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_RATE_LIMITED,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message="GDELT rate limit exceeded (HTTP 429).",
                http_status=429,
            )

        if resp.status_code >= 500:
            logger.warning("GDELT returned 5xx server error %d", resp.status_code)
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_PROVIDER_UNAVAILABLE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message=f"GDELT server error (HTTP {resp.status_code}).",
                http_status=resp.status_code,
            )

        if resp.status_code != 200:
            logger.warning("GDELT returned unexpected HTTP status %d", resp.status_code)
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_PROVIDER_UNAVAILABLE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message=f"GDELT returned HTTP {resp.status_code}.",
                http_status=resp.status_code,
            )

        content_type = (resp.headers.get("content-type") or "").lower()
        if "text/html" in content_type and "json" not in content_type:
            logger.warning("GDELT returned HTML error page instead of JSON")
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_INVALID_RESPONSE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message="GDELT returned HTML instead of expected JSON format.",
            )

        try:
            data = resp.json()
        except Exception as e:
            logger.warning("Failed to decode GDELT JSON response: %s", str(e))
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_INVALID_RESPONSE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message="GDELT response contained invalid JSON.",
            )

        if not isinstance(data, dict):
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_INVALID_RESPONSE,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
                error_message="GDELT response payload was not a valid dictionary.",
            )

        raw_articles = data.get("articles")
        if raw_articles is None:
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_NO_RESULTS,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
            )

        if not isinstance(raw_articles, list) or len(raw_articles) == 0:
            return ProviderFetchResult(
                source_id=source_id,
                source_name=source_name,
                source_type="gdelt",
                status=STATUS_NO_RESULTS,
                articles=[],
                items_count=0,
                duration_ms=duration_ms,
            )

        normalized: List[NormalizedArticle] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in raw_articles:
            if not isinstance(item, dict):
                continue
            url = item.get("url") or ""
            title = item.get("title") or "Untitled"
            if not url or not title:
                continue

            canon_url = canonicalize_url(url)
            article_id = hashlib.sha256(canon_url.encode("utf-8")).hexdigest()[:16]
            domain = item.get("domain") or "GDELT Source"

            raw_seendate = str(item.get("seendate") or "")
            parsed_date = ""
            if raw_seendate:
                try:
                    if "T" in raw_seendate and raw_seendate.endswith("Z"):
                        dt = datetime.strptime(raw_seendate, "%Y%m%dT%H%M%SZ").replace(
                            tzinfo=timezone.utc
                        )
                        parsed_date = dt.isoformat()
                    else:
                        parsed_date = raw_seendate
                except Exception:
                    parsed_date = raw_seendate

            normalized.append(
                NormalizedArticle(
                    id=f"gdelt_{article_id}",
                    title=title.strip(),
                    url=canon_url,
                    publisher=domain.strip(),
                    published_at=parsed_date,
                    ingested_at=now_iso,
                    source_type="gdelt",
                    summary="",
                    language=item.get("language", "English"),
                    country=item.get("sourcecountry", country or "IN"),
                    query=keyword,
                    raw_metadata=item,
                )
            )

        return ProviderFetchResult(
            source_id=source_id,
            source_name=source_name,
            source_type="gdelt",
            status=STATUS_SUCCESS if normalized else STATUS_NO_RESULTS,
            articles=normalized,
            items_count=len(normalized),
            duration_ms=duration_ms,
            http_status=200,
        )
