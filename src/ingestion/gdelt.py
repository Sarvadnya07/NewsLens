"""GDELT 2.0 Doc API ingestion module for NewsLens India.

Designed with robust rate-limiting, error handling, and article normalization.
Reuses query concepts from research/gdelt-doc-api with production hardening.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.models import NormalizedArticle, canonicalize_url

logger = logging.getLogger(__name__)

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltClient:
    """Client for GDELT 2.0 Doc API with rate throttling, retries, and resilient parsing."""

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

    def _throttle(self):
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
        """
        Executes an article search against GDELT Doc API and returns normalized articles.
        Handles empty responses, 429 rate limits, and network errors gracefully.
        """
        if not keyword or not keyword.strip():
            return []

        # Construct GDELT query string
        parts = []
        cleaned_kw = keyword.strip()
        if " " in cleaned_kw:
            parts.append(f'"{cleaned_kw}"')
        else:
            parts.append(cleaned_kw)

        if country:
            parts.append(f"sourcecountry:{country}")

        if language:
            # GDELT v2 doc API uses 3-letter or formal lang codes (e.g., eng / English)
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

        headers = {"User-Agent": "NewsLens-India-Agent/1.0 (Academic Research; Python 3.12)"}

        resp = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                self._last_request_time = time.time()
                resp = requests.get(
                    GDELT_DOC_ENDPOINT, params=params, headers=headers, timeout=self.request_timeout
                )
                break
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < self.max_retries:
                    logger.warning(
                        "GDELT request attempt %d failed (%s). Retrying in %.1fs...",
                        attempt + 1,
                        str(e),
                        self.retry_delay_seconds,
                    )
                    time.sleep(self.retry_delay_seconds)
                else:
                    logger.warning(
                        "GDELT request timed out or connection failed after %d attempts: %s",
                        attempt + 1,
                        str(e),
                    )
                    return []
            except (requests.exceptions.RequestException, Exception) as e:
                logger.error("GDELT network request failed: %s", str(e))
                return []

        if resp is None:
            return []

        if resp.status_code == 429:
            logger.warning("GDELT returned 429 Rate Limited. Response: %s", resp.text[:120])
            return []

        if resp.status_code != 200:
            logger.warning("GDELT returned non-200 status code: %d", resp.status_code)
            return []

        content_type = resp.headers.get("content-type", "")
        if "json" not in content_type and "text/html" in content_type:
            # GDELT sends 200 with HTML message on malformed query or internal error
            logger.warning("GDELT returned HTML instead of JSON: %s", resp.text[:120])
            return []

        try:
            data = resp.json()
        except Exception as e:
            logger.warning("Failed to decode GDELT JSON response: %s", str(e))
            return []

        raw_articles = data.get("articles", [])
        if not raw_articles:
            return []

        normalized: List[NormalizedArticle] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in raw_articles:
            url = item.get("url") or ""
            title = item.get("title") or "Untitled"
            if not url or not title:
                continue

            canon_url = canonicalize_url(url)
            article_id = hashlib.sha256(canon_url.encode("utf-8")).hexdigest()[:16]
            domain = item.get("domain") or "GDELT Source"

            # Parse GDELT seendate (e.g. '20261030T100000Z') into readable ISO
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

        return normalized
