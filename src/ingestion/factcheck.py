"""Google Fact Check Tools API client for NewsLens India.

Integrates Google Fact Check Tools API (https://factchecktools.googleapis.com)
for ClaimReview evidence retrieval. Stores structured claim verifications
separately from standard news articles.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from src.config import sanitize_text, settings
from src.models import FactCheckClaimRecord
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)

FACTCHECK_API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


class GoogleFactCheckClient:
    """Client for Google Fact Check Tools ClaimReview search with local persistence."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        db: Optional[DatabaseManager] = None,
        request_timeout: float = 15.0,
    ):
        self.api_key = settings.GOOGLE_FACTCHECK_API_KEY if api_key is None else api_key
        self.db = db
        self.request_timeout = request_timeout or settings.INTEGRATION_REQUEST_TIMEOUT
        self.daily_budget = settings.GOOGLE_FACTCHECK_DAILY_BUDGET
        self.min_refresh_interval = settings.GOOGLE_FACTCHECK_MIN_REFRESH_INTERVAL

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self.api_key and str(self.api_key).strip())

    @property
    def is_enabled(self) -> bool:
        """Returns True if Google Fact Check is enabled in settings and configured."""
        return bool(settings.GOOGLE_FACTCHECK_ENABLED and self.is_configured)

    def test_connection(self) -> Dict[str, Any]:
        """Performs a minimal bounded authenticated request to verify API credentials."""
        if not self.is_configured:
            return {
                "success": False,
                "status": "not_configured",
                "message": "Google Fact Check API key is not configured.",
                "http_status": None,
                "latency_ms": 0.0,
            }

        start = time.perf_counter()
        params: Dict[str, Any] = {
            "key": (self.api_key or "").strip(),
            "query": "India",
            "pageSize": 1,
        }

        try:
            resp = requests.get(
                FACTCHECK_API_URL,
                params=params,
                timeout=self.request_timeout,
            )
            duration_ms = (time.perf_counter() - start) * 1000

            if resp.status_code == 200:
                return {
                    "success": True,
                    "status": "connected",
                    "message": "Successfully authenticated with Google Fact Check Tools API.",
                    "http_status": 200,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code in (400, 403):
                return {
                    "success": False,
                    "status": "authentication_failed",
                    "message": "Invalid Google Cloud API key or Fact Check Tools API not enabled.",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
            elif resp.status_code == 429:
                return {
                    "success": False,
                    "status": "rate_limited",
                    "message": "Google Fact Check Tools API quota exceeded.",
                    "http_status": 429,
                    "latency_ms": duration_ms,
                }
            else:
                return {
                    "success": False,
                    "status": "provider_unavailable",
                    "message": f"Google Fact Check API error (HTTP {resp.status_code}).",
                    "http_status": resp.status_code,
                    "latency_ms": duration_ms,
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "status": "timeout",
                "message": "Connection to Google Fact Check Tools API timed out.",
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

    def search_claims(
        self,
        query: str,
        language_code: Optional[str] = None,
        max_age_days: Optional[int] = None,
        page_size: int = 10,
        article_id: Optional[str] = None,
    ) -> List[FactCheckClaimRecord]:
        """Queries Google Fact Check Tools API and persists ClaimReview results."""
        if not self.is_configured or not query or not query.strip():
            return []

        params: Dict[str, Any] = {
            "key": (self.api_key or "").strip(),
            "query": query.strip(),
            "pageSize": min(page_size, 20),
        }
        if language_code:
            params["languageCode"] = language_code
        if max_age_days:
            params["maxAgeDays"] = max_age_days

        records: List[FactCheckClaimRecord] = []

        try:
            resp = requests.get(
                FACTCHECK_API_URL,
                params=params,
                timeout=self.request_timeout,
            )
            if resp.status_code != 200:
                logger.warning(
                    "Fact Check API search failed (HTTP %s): %s", resp.status_code, resp.text[:200]
                )
                return []

            data = resp.json()
            claims_raw = data.get("claims", [])
            for item in claims_raw:
                claim_text = item.get("text", "")
                claimant = item.get("claimant")
                claim_date = item.get("claimDate")

                for review in item.get("claimReview", []):
                    pub = review.get("publisher", {})
                    pub_name = pub.get("name", "Unknown Fact Checker")
                    pub_site = pub.get("site")
                    fact_url = review.get("url", "")
                    rating_text = review.get("textualRating", "")
                    review_date = review.get("reviewDate")
                    lang = review.get("languageCode", language_code or "en")

                    # Deduplication ID from review URL or claim text hash
                    hash_src = f"{fact_url}_{claim_text}"
                    cid = f"fc_{hashlib.sha256(hash_src.encode('utf-8')).hexdigest()[:16]}"

                    rating_std = self._standardize_rating(rating_text)

                    rec = FactCheckClaimRecord(
                        id=cid,
                        claim_text=claim_text,
                        claimant=claimant,
                        claim_date=claim_date,
                        rating_text=rating_text,
                        rating_standardized=rating_std,
                        publisher_name=pub_name,
                        publisher_site=pub_site,
                        fact_check_url=fact_url,
                        review_date=review_date,
                        language_code=lang,
                        matched_article_id=article_id,
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        raw_metadata=item,
                    )
                    records.append(rec)

            if self.db and records:
                self.persist_claims(records)

            return records
        except Exception as exc:
            logger.error("Error searching Google Fact Check API: %s", sanitize_text(str(exc)))
            return []

    def persist_claims(self, claims: List[FactCheckClaimRecord]) -> int:
        """Stores structured claim review records in SQLite fact_check_claims table."""
        if not self.db or not claims:
            return 0

        inserted = 0
        with self.db._connect() as conn:
            cursor = conn.cursor()
            for c in claims:
                cursor.execute(
                    """
                    INSERT INTO fact_check_claims (
                        id, claim_text, claimant, claim_date, rating_text,
                        rating_standardized, publisher_name, publisher_site,
                        fact_check_url, review_date, language_code,
                        matched_article_id, retrieved_at, raw_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        rating_text=excluded.rating_text,
                        rating_standardized=excluded.rating_standardized,
                        matched_article_id=COALESCE(excluded.matched_article_id, fact_check_claims.matched_article_id),
                        retrieved_at=excluded.retrieved_at
                    """,
                    (
                        c.id,
                        c.claim_text,
                        c.claimant,
                        c.claim_date,
                        c.rating_text,
                        c.rating_standardized,
                        c.publisher_name,
                        c.publisher_site,
                        c.fact_check_url,
                        c.review_date,
                        c.language_code,
                        c.matched_article_id,
                        c.retrieved_at,
                        json.dumps(c.raw_metadata),
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1

        return inserted

    @staticmethod
    def _standardize_rating(rating: str) -> str:
        """Standardizes editorial fact-check rating text into high-level categories."""
        if not rating:
            return "unverified"
        r = rating.lower().strip()
        if any(w in r for w in ("false", "fake", "incorrect", "debunked", "hoax", "fabricated")):
            return "false"
        if any(w in r for w in ("misleading", "partly", "half", "missing context", "exaggerated")):
            return "misleading"
        if any(w in r for w in ("true", "correct", "verified", "accurate")):
            return "true"
        return "unverified"
