"""Service layer for graph-based coverage and source relationship analysis.

Provides the structured results needed by the Evidence & Coverage page and
the Methodology page: coverage groups, similarity edges, publisher
distribution, and diversity metrics.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.models import NormalizedArticle
from src.processing.coverage_graph import (
    CoverageGraphBuilder,
    CoverageGroup,
)

logger = logging.getLogger(__name__)


class CoverageService:
    """Service for building and querying the article similarity graph."""

    def __init__(
        self,
        similarity_threshold: float = 0.55,
        max_articles: int = 200,
        cache_dir: str = "models/graph_cache",
    ):
        self.graph_builder = CoverageGraphBuilder(
            similarity_threshold=similarity_threshold,
            max_articles=max_articles,
            cache_dir=cache_dir,
        )

    def get_coverage_groups(
        self,
        articles: Optional[List[NormalizedArticle]] = None,
        max_articles: int = 200,
        time_window_days: int = 30,
    ) -> List[CoverageGroup]:
        """Return coverage clusters for the given (or recent) articles."""
        if articles is None:
            articles = self._get_recent_articles(max_articles, time_window_days)
        if not articles:
            return []

        if len(articles) > max_articles:
            logger.warning(
                "Requesting graph over %d articles exceeds limit of %d; trimming.",
                len(articles),
                max_articles,
            )
            # Keep the most recent articles for consistent, bounded processing
            articles = articles[:max_articles]

        groups = self.graph_builder.find_connected_components(articles)
        return groups

    def get_similar_articles_to(
        self, target_article: NormalizedArticle, articles: List[NormalizedArticle], top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """Find articles similar to a target article."""
        if not articles:
            return []

        self.graph_builder._ensure_index_ready(articles)
        sim_matrix = self.graph_builder._tfidf_matrix

        target_idx = None
        for i, a in enumerate(articles):
            if a.id == target_article.id:
                target_idx = i
                break

        if target_idx is None:
            return []

        target_vec = sim_matrix[target_idx : target_idx + 1]
        sims = (target_vec @ sim_matrix.T).toarray()[0]

        results = []
        for i, sim in enumerate(sims):
            if i == target_idx:
                continue
            rel = self.graph_builder._classify_relationship(float(sim))
            if rel != "unrelated":
                results.append(
                    {
                        "article_id": articles[i].id,
                        "title": articles[i].title,
                        "publisher": articles[i].publisher,
                        "similarity": round(float(sim), 4),
                        "relationship": rel,
                    }
                )

        results.sort(key=lambda x: -x["similarity"])
        return results[:top_n]

    def compute_coverage_metrics(
        self, articles: List[NormalizedArticle]
    ) -> Dict[str, Any]:
        """Compute aggregate coverage metrics for a set of articles."""
        total = len(articles)
        publishers: Dict[str, int] = {}
        for a in articles:
            name = a.publisher or "Unknown"
            publishers[name] = publishers.get(name, 0) + 1

        distinct_pub = len(publishers)
        n = total if total > 0 else 1

        # Shannon entropy
        probs = [c / n for c in publishers.values()]
        entropy = float(-sum(p * __import__("math").log2(p) for p in probs if p > 0))

        # Normalized entropy
        max_ent = __import__("math").log2(distinct_pub) if distinct_pub > 1 else 1.0
        norm_entropy = entropy / max_ent if max_ent > 0 else 0.0

        return {
            "total_articles": total,
            "distinct_publishers": distinct_pub,
            "publisher_distribution": dict(publishers),
            "publisher_diversity_entropy": round(entropy, 4),
            "publisher_diversity_normalized": round(norm_entropy, 4),
        }

    def _get_recent_articles(
        self, limit: int = 200, time_window_days: int = 30
    ) -> List[NormalizedArticle]:
        """Retrieve recent articles within a time window.

        This is a simplified fallback; the full implementation should query
        the database.  For now, we rely on the caller to provide articles.
        """
        # Import here to avoid circular dependency
        from src.services.news_service import NewsLensService

        service = NewsLensService()
        return service.get_recent_articles(limit=limit)
