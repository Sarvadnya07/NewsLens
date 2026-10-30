"""GDELT 2.0 Doc API ingestion module for NewsLens India.

Designed with robust rate-limiting, error handling, and article normalization.
Reuses query concepts from research/gdelt-doc-api with production hardening.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import requests

from src.models import NormalizedArticle

logger = logging.getLogger(__name__)

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltClient:
    """Client for GDELT 2.0 Doc API with rate throttling and resilient parsing."""

    def __init__(self, request_timeout: int = 10, min_interval_seconds: float = 5.0):
        self.request_timeout = request_timeout
        self.min_interval_seconds = min_interval_seconds
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
        max_records: int = 30
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
            parts.append(f"sourcelang:{language}")

        query_str = " ".join(parts)
        params = {
            "query": query_str,
            "mode": "artlist",
            "format": "json",
            "maxrecords": min(max(max_records, 1), 250)
        }
        if timespan:
            params["timespan"] = timespan

        headers = {
            "User-Agent": "NewsLens-India-Agent/1.0 (Academic Research; Python 3.13)"
        }

        self._throttle()
        try:
            self._last_request_time = time.time()
            resp = requests.get(
                GDELT_DOC_ENDPOINT,
                params=params,
                headers=headers,
                timeout=self.request_timeout
            )
        except requests.exceptions.Timeout:
            logger.warning("GDELT request timed out after %ds", self.request_timeout)
            return []
        except (requests.exceptions.RequestException, Exception) as e:
            logger.error("GDELT network request failed: %s", str(e))
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

            article_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            domain = item.get("domain") or "GDELT Source"
            seendate = item.get("seendate") or now_iso

            normalized.append(NormalizedArticle(
                id=f"gdelt_{article_id}",
                title=title.strip(),
                url=url.strip(),
                publisher=domain.strip(),
                published_at=seendate,
                ingested_at=now_iso,
                source_type="gdelt",
                summary="",
                language=item.get("language", "English"),
                country=item.get("sourcecountry", country or "IN"),
                query=keyword,
                raw_metadata=item
            ))

        return normalized
