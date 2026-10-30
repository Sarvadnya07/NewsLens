"""Application service layer orchestrating Ingestion, ML, Retrieval, and Storage."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.ingestion.gdelt import GdeltClient
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
        self, db_path: str = "data/newslens.db", fact_checks_path: str = "data/fact_checks.json"
    ):
        self.db = DatabaseManager(db_path=db_path)
        self.gdelt = GdeltClient()
        self.rss = RssIngestionService()
        self.ml_model = FakeNewsScreeningModel()
        self.retriever = FactCheckRetriever(data_path=fact_checks_path)
        self.deduplicator = NewsDeduplicator()

    # --- Ingestion & Storage ---

    def refresh_rss_feeds(self) -> Dict[str, Any]:
        """Fetches latest stories from all configured Indian publisher RSS feeds and stores them."""
        logger.info("Executing RSS feed refresh...")
        result = self.rss.fetch_all()
        articles = result.get("articles", [])
        stats = result.get("stats", {})

        inserted_count = self.db.upsert_articles(articles)

        # Update source statuses
        for name, info in stats.items():
            self.db.record_source_status(
                source_name=name,
                source_type="rss",
                status=info.get("status", "unknown"),
                items_fetched=info.get("count", 0),
                error_message=info.get("error"),
            )

        return {"total_fetched": len(articles), "new_stored": inserted_count, "stats": stats}

    def search_gdelt(self, query: str, max_records: int = 25) -> List[NormalizedArticle]:
        """Queries GDELT Doc API for Indian news topic and persists results."""
        if not query or not query.strip():
            return []

        articles = self.gdelt.search_articles(keyword=query, max_records=max_records)
        if articles:
            self.db.upsert_articles(articles)
            self.db.record_source_status(
                source_name=f"GDELT: {query}",
                source_type="gdelt",
                status="success",
                items_fetched=len(articles),
            )
        else:
            self.db.record_source_status(
                source_name=f"GDELT: {query}",
                source_type="gdelt",
                status="empty_or_rate_limited",
                items_fetched=0,
            )
        return articles

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
            else f"manual://{hashlib.sha256(title.encode()).hexdigest()[:32]}"
        )
        art_id = f"manual_{hashlib.sha256(dummy_url.encode()).hexdigest()[:16]}"

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

    def get_recent_articles(
        self, query: Optional[str] = None, source_type: Optional[str] = None, limit: int = 50
    ) -> List[NormalizedArticle]:
        """Fetches stored articles from SQLite."""
        return self.db.get_articles(query=query, source_type=source_type, limit=limit)

    def get_source_statuses(self) -> List[Dict[str, Any]]:
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
