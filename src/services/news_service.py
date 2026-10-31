"""Application service layer orchestrating Ingestion, ML, Retrieval, and Storage."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.ingestion.gdelt import GdeltClient
from src.ingestion.models import (
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_SUCCESS,
    ProviderFetchResult,
    RefreshResult,
)
from src.ingestion.rss import RssIngestionService
from src.ml.predict import FakeNewsScreeningModel
from src.models import NormalizedArticle, canonicalize_url
from src.processing.deduplication import NewsDeduplicator
from src.retrieval.fact_check import FactCheckRetriever
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class NewsLensService:
    """Central orchestration service for NewsLens India."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        fact_checks_path: Optional[str] = None,
    ):
        # Environment overrides let deployments and tests point the service at
        # a different datastore without editing source defaults.
        db_path = db_path or os.environ.get("NEWSLENS_DB_PATH", "data/newslens.db")
        fact_checks_path = fact_checks_path or os.environ.get(
            "NEWSLENS_FACT_CHECKS_PATH", "data/fact_checks.json"
        )
        self.db = DatabaseManager(db_path=db_path)
        self.gdelt = GdeltClient()
        self.rss = RssIngestionService()
        self.ml_model = FakeNewsScreeningModel()
        self.retriever = FactCheckRetriever(data_path=fact_checks_path)
        self.deduplicator = NewsDeduplicator()

    # --- Ingestion & Storage ---

    def refresh_rss_feeds(self) -> RefreshResult:
        """Synchronously polls all configured Indian publisher RSS feeds.

        Upserts articles into SQLite, records per-feed health outcomes, and
        returns a structured RefreshResult preserving partial successes.
        """
        start_time = time.perf_counter()
        logger.info("Executing synchronous RSS feed refresh...")
        result = self.rss.fetch_all()
        articles: List[NormalizedArticle] = result.get("articles", [])
        stats: Dict[str, Dict[str, Any]] = result.get("stats", {})
        provider_results: Dict[str, ProviderFetchResult] = result.get("provider_results", {})

        inserted_count = self.db.upsert_articles(articles)

        # Update per-source status in SQLite
        for name, info in stats.items():
            self.db.record_source_status(
                source_name=name,
                source_type="rss",
                status=info.get("status", STATUS_PROVIDER_UNAVAILABLE),
                items_fetched=info.get("count", 0),
                error_message=info.get("error"),
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        all_succeeded = (
            all(res.status == STATUS_SUCCESS for res in provider_results.values())
            if provider_results
            else False
        )
        all_failed = (
            all(res.status != STATUS_SUCCESS for res in provider_results.values())
            if provider_results
            else True
        )

        return RefreshResult(
            total_fetched=len(articles),
            new_stored=inserted_count,
            duration_ms=duration_ms,
            provider_results=provider_results,
            all_succeeded=all_succeeded,
            all_failed=all_failed,
        )

    def search_gdelt(self, query: str, max_records: int = 25) -> ProviderFetchResult:
        """Queries GDELT Doc API for Indian news topic and persists results."""
        if not query or not query.strip():
            return ProviderFetchResult(
                source_id="gdelt",
                source_name="GDELT",
                source_type="gdelt",
                status=STATUS_NO_RESULTS,
                articles=[],
                items_count=0,
                duration_ms=0.0,
            )

        result = self.gdelt.fetch_articles(keyword=query.strip(), max_records=max_records)
        if result.articles:
            self.db.upsert_articles(result.articles)

        self.db.record_source_status(
            source_name=f"GDELT: {query.strip()}",
            source_type="gdelt",
            status=result.status,
            items_fetched=result.items_count,
            error_message=result.error_message,
        )
        return result

    def submit_manual_article(
        self,
        title: str,
        publisher: str = "Manual User Submission",
        url: str = "",
        summary: str = "",
    ) -> NormalizedArticle:
        """Stores a user-submitted article/headline for monitoring and tracking."""
        now_iso = datetime.now(timezone.utc).isoformat()
        dummy_url = (
            canonicalize_url(url.strip())
            if url and url.strip()
            else f"manual://{hashlib.sha256(title.encode('utf-8')).hexdigest()[:32]}"
        )
        art_id = f"manual_{hashlib.sha256(dummy_url.encode('utf-8')).hexdigest()[:16]}"

        article = NormalizedArticle(
            id=art_id,
            title=title.strip(),
            url=dummy_url,
            publisher=publisher.strip() or "Manual Submission",
            published_at=now_iso,
            ingested_at=now_iso,
            source_type="manual",
            summary=summary.strip(),
            language="en",
            country="IN",
            query="manual",
        )
        self.db.upsert_article(article)
        return article

    def get_distinct_publishers(self) -> List[str]:
        """Publishers that actually have stored coverage (for the monitor filter)."""
        return self.db.get_distinct_publishers()

    def query_monitor_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_order: str = "Recency",
        publisher: Optional[str] = None,
        days: Optional[int] = None,
        order_by: str = "ingested_at",
    ) -> Dict[str, Any]:
        """Provides a clean, composable service contract for the News Monitor.

        ``days`` limits results to the trailing window measured against the
        effective publication date (falling back to ingestion date when a
        publisher supplied no usable timestamp).

        Returns:
          - articles: List of matching NormalizedArticle objects for current page.
          - total_matching: Total matching records across the entire dataset.
          - page: Current page number (1-indexed).
          - page_size: Limit passed.
          - total_pages: Number of pages available for the current filters.
          - applied_filters: Dictionary summarizing applied parameters.
        """
        clean_query = query.strip() if query and query.strip() else None
        clean_source = source_type.strip().lower() if source_type and source_type.strip() else None
        if clean_source in ("all", "none"):
            clean_source = None
        clean_publisher = publisher.strip() if publisher and publisher.strip() else None

        since_iso: Optional[str] = None
        if days and days > 0:
            since_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        limit = max(int(limit), 1)
        offset = max(int(offset), 0)
        ascending = "Chronological" in sort_order or "Oldest" in sort_order

        articles = self.db.get_articles(
            query=clean_query,
            source_type=clean_source,
            publisher=clean_publisher,
            since_iso=since_iso,
            limit=limit,
            offset=offset,
            order_by=order_by,
            ascending=ascending,
        )
        total_matching = self.db.count_matching_articles(
            query=clean_query,
            source_type=clean_source,
            publisher=clean_publisher,
            since_iso=since_iso,
        )

        total_pages = (total_matching + limit - 1) // limit if total_matching else 0
        return {
            "articles": articles,
            "total_matching": total_matching,
            "page": (offset // limit) + 1,
            "page_size": limit,
            "total_pages": total_pages,
            "applied_filters": {
                "query": clean_query,
                "source_type": clean_source,
                "publisher": clean_publisher,
                "days": days,
                "sort_order": sort_order,
                "order_by": order_by,
            },
        }

    def get_recent_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NormalizedArticle]:
        """Fetches stored articles from SQLite."""
        return self.db.get_articles(
            query=query,
            source_type=source_type,
            limit=limit,
            offset=offset,
        )

    def get_source_statuses(self) -> List[Dict[str, Any]]:
        """Returns recorded source health statuses."""
        return self.db.get_all_source_status()

    # --- Analysis & Screening ---

    def screen_article_text(self, text: str) -> Dict[str, Any]:
        """Runs ML linguistic fake news screening on article headline or text."""
        return self.ml_model.predict(text)

    # --- Evidence & Fact-Check Retrieval ---

    def retrieve_fact_checks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieves matching fact check claims using BM25Plus ranking."""
        return self.retriever.retrieve(query=query, top_k=top_k)

    # --- Duplicate & Related Coverage ---

    def analyze_coverage_clusters(
        self, articles: Optional[List[NormalizedArticle]] = None
    ) -> List[Dict[str, Any]]:
        """Finds multi-publisher story clusters and duplicate reports."""
        target_articles = articles if articles is not None else self.get_recent_articles(limit=100)
        return self.deduplicator.find_related_and_duplicates(target_articles)

    def find_related_news(self, query_text: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Finds existing coverage relevant to an analyzed text snippet."""
        recent = self.get_recent_articles(limit=150)
        return self.deduplicator.find_related_to_query(query_text, recent, top_n=top_n)
