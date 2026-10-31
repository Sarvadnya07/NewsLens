"""Graph-based news coverage and source relationship analysis.

Builds a lightweight article similarity graph from stored news records,
computes connected components, publisher distribution and diversity metrics
(Shannon entropy, normalized entropy) without external graph dependencies.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import NormalizedArticle
from src.preprocessing.cleaner import clean_text, tokenize_text

logger = logging.getLogger(__name__)

# Graph construction thresholds
DEFAULT_SIMILARITY_THRESHOLD = 0.55
DEFAULT_EXACT_THRESHOLD = 0.90

# Maximum number of articles to consider for graph construction per call
DEFAULT_MAX_GRAPH_ARTICLES = 200

# Coverage time window in days for default article selection
DEFAULT_COVERAGE_WINDOW_DAYS = 30

# Cache directory for graph artifacts
GRAPH_CACHE_DIR = "models/graph_cache"
GRAPH_CACHE_VERSION = "1.0"


@dataclass(frozen=True)
class ArticleEdge:
    """A similarity relationship between two articles."""

    source_article_id: str
    target_article_id: str
    similarity: float
    similarity_method: str
    relationship: str
    matched_ngrams: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_article_id": self.source_article_id,
            "target_article_id": self.target_article_id,
            "similarity": round(self.similarity, 4),
            "similarity_method": self.similarity_method,
            "relationship": self.relationship,
            "matched_ngrams": self.matched_ngrams,
        }


@dataclass(frozen=True)
class CoverageGroup:
    """A connected component / coverage cluster from the article graph."""

    group_id: str
    article_ids: List[str] = field(default_factory=list)
    publisher_ids: Set[str] = field(default_factory=set)
    publisher_names: Set[str] = field(default_factory=set)
    article_count: int = 0
    distinct_publisher_count: int = 0
    similarity_relationships: List[ArticleEdge] = field(default_factory=list)
    duplicate_relationships: List[ArticleEdge] = field(default_factory=list)
    possible_syndication_relationships: List[ArticleEdge] = field(default_factory=list)
    publisher_distribution: Dict[str, int] = field(default_factory=dict)
    publisher_diversity: float = 0.0
    provenance_status: List[str] = field(default_factory=list)
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coverage_group_id": self.group_id,
            "article_ids": self.article_ids,
            "publishers": sorted(self.publisher_names),
            "distinct_publisher_count": self.distinct_publisher_count,
            "article_count": self.article_count,
            "similarity_relationships": [
                e.to_dict() for e in self.similarity_relationships
            ],
            "duplicate_relationships": [
                e.to_dict() for e in self.duplicate_relationships
            ],
            "possible_syndication_relationships": [
                e.to_dict() for e in self.possible_syndication_relationships
            ],
            "publisher_distribution": self.publisher_distribution,
            "publisher_diversity": round(self.publisher_diversity, 4),
            "provenance_status": self.provenance_status,
            "last_updated": self.last_updated,
        }
class CoverageGraphBuilder:
    """Builds and explores the article similarity graph.

    Uses TF-IDF cosine similarity for candidate generation and a
    lightweight union-find (disjoint-set) structure for connected
    components.  Does not require NetworkX or similar graph libraries.
    """

    def __init__(
        self,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        max_articles: int = DEFAULT_MAX_GRAPH_ARTICLES,
        cache_dir: str = GRAPH_CACHE_DIR,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_articles = max_articles
        self.cache_dir = cache_dir
        self._vectorizer = None
        self._article_index: Dict[str, NormalizedArticle] = {}
        self._tfidf_matrix = None
        self._article_cache_hash: Optional[str] = None

    def _cache_key(self, articles: List[NormalizedArticle]) -> str:
        """Create a deterministic cache identifier for the article set."""
        payload = "|".join(
            f"{a.id}|{a.title}|{a.publisher}|{a.url}|{(a.published_at or '')}"
            for a in articles
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _load_cache(self, articles: List[NormalizedArticle]) -> bool:
        """Check if cached graph data exists for this article set."""
        cache_key = self._cache_key(articles)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.npy")
        if os.path.exists(cache_file):
            try:
                data = np.load(cache_file, allow_pickle=True).item()
                self._vectorizer = data.get("vectorizer")
                self._article_index = data.get("articles", {})
                self._tfidf_matrix = data.get("tfidf_matrix")
                self._article_cache_hash = cache_key
                logger.info("Loaded graph cache: %s", cache_key)
                return True
            except Exception as e:
                logger.warning("Cache load failed: %s", e)
        return False

    def _save_cache(self, articles: List[NormalizedArticle]) -> None:
        """Persist graph data for future reuse."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        cache_key = self._cache_key(articles)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.npy")
        try:
            data = {
                "vectorizer": self._vectorizer,
                "articles": self._article_index,
                "tfidf_matrix": self._tfidf_matrix,
            }
            np.save(cache_file, data, allow_pickle=True)
            logger.info("Saved graph cache: %s", cache_key)
        except Exception as e:
            logger.warning("Cache save failed: %s", e)

    def _build_tf_matrix(self, articles: List[NormalizedArticle]) -> None:
        """Fit TF-IDF matrix on article titles (or summaries)."""
        titles = [clean_text(a.title) for a in articles]
        self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
        self._tfidf_matrix = self._vectorizer.fit_transform(titles)
        self._article_index = {a.id: a for a in articles}

    def _ensure_index_ready(self, articles: List[NormalizedArticle]) -> None:
        """Load cache or build fresh TF-IDF index."""
        if self._load_cache(articles):
            return
        self._build_tf_matrix(articles)
        self._save_cache(articles)

    def _find(self, parent: List[int], i: int) -> int:
        """Find root of element i with path compression."""
        if parent[i] != i:
            parent[i] = self._find(parent, parent[i])
        return parent[i]

    def _union(self, parent: List[int], rank: List[int], x: int, y: int) -> None:
        """Union two sets by rank."""
        xroot = self._find(parent, x)
        yroot = self._find(parent, y)
        if xroot == yroot:
            return
        if rank[xroot] < rank[yroot]:
            parent[xroot] = yroot
        elif rank[xroot] > rank[yroot]:
            parent[yroot] = xroot
        else:
            parent[yroot] = xroot
            rank[xroot] += 1

    def _build_connected_components(
        self, articles: List[NormalizedArticle]
    ) -> Tuple[np.ndarray, np.ndarray, Dict[int, List[int]]]:
        """Build TF-IDF sim matrix and find connected components."""
        n = len(articles)
        sim_matrix = np.eye(n, dtype=float)

        # Compute pairwise cosine similarity for all articles
        if n > 1 and self._tfidf_matrix is not None:
            sim_matrix = cosine_similarity(self._tfidf_matrix)

        # Union-find for connected components with threshold
        parent = list(range(n))
        rank = [0] * n

        for i in range(n):
            for j in range(i + 1, n):
                if sim_matrix[i, j] >= self.similarity_threshold:
                    self._union(parent, rank, i, j)

        # Group by root
        components: Dict[int, List[int]] = {}
        for i in range(n):
            root = self._find(parent, i)
            if root not in components:
                components[root] = []
            components[root].append(i)

        return sim_matrix, parent, components

    def build_graph(
        self, articles: List[NormalizedArticle]
    ) -> Tuple[np.ndarray, np.ndarray, Dict[int, List[int]]]:
        """Ensure index is ready and build the similarity graph."""
        self._ensure_index_ready(articles)
        return self._build_connected_components(articles)

    def find_connected_components(
        self, articles: List[NormalizedArticle]
    ) -> List[CoverageGroup]:
        """Identify connected components / coverage clusters."""
        if len(articles) == 0:
            return []

        self._ensure_index_ready(articles)
        _, parent, components = self._build_connected_components(articles)

        groups: List[CoverageGroup] = []
        for root_idx, indices in components.items():
            if len(indices) < 2:
                continue
            group_articles = [articles[i] for i in indices]
            group_ids = [a.id for a in group_articles]
            publisher_names = {a.publisher for a in group_articles}
            publisher_ids = {a.id for a in group_articles}

            # Compute publisher distribution
            distribution: Dict[str, int] = {}
            for a in group_articles:
                name = a.publisher or "Unknown"
                distribution[name] = distribution.get(name, 0) + 1

            # Compute Shannon entropy
            total = len(group_articles)
            probs = np.array(list(distribution.values()), dtype=float)
            probs = probs / probs.sum()
            entropy = float(-np.sum(probs * np.log2(probs)))
            max_entropy = np.log2(len(distribution)) if len(distribution) > 1 else 1.0
            norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

            # Build relationship edges
            edges = []
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    sim = float(
                        self._tfidf_matrix[indices[i]]
                        @ self._tfidf_matrix[indices[j]].T
                    ).item()
                    rel = self._classify_relationship(sim)
                    edges.append(
                        ArticleEdge(
                            source_article_id=group_articles[i].id,
                            target_article_id=group_articles[j].id,
                            similarity=round(sim, 4),
                            similarity_method="tfidf_cosine",
                            relationship=rel,
                        )
                    )

            groups.append(
                CoverageGroup(
                    group_id=f"cg_{root_idx}_{hashlib.md5((root_idx).__str__().encode()).hexdigest()[:8]}",
                    article_ids=group_ids,
                    publisher_ids=publisher_ids,
                    publisher_names=publisher_names,
                    article_count=len(group_articles),
                    distinct_publisher_count=len(distribution),
                    similarity_relationships=edges,
                    duplicate_relationships=[
                        e for e in edges if e.relationship == "exact_or_republished"
                    ],
                    possible_syndication_relationships=[
                        e for e in edges if e.relationship == "likely_syndicated"
                    ],
                    publisher_distribution=distribution,
                    publisher_diversity=round(norm_entropy, 4),
                    provenance_status=["Distinct publishers observed"],
                )
            )

        return sorted(groups, key=lambda g: g.article_count, reverse=True)

    def _classify_relationship(self, sim: float) -> str:
        """Classify a similarity score into a relationship tier."""
        if sim >= DEFAULT_EXACT_THRESHOLD:
            return "exact_or_republished"
        elif sim >= 0.70:
            return "likely_syndicated"
        elif sim >= self.similarity_threshold:
            return "similar_coverage"
        return "unrelated"

    def compute_publisher_diversity(
        self, groups: List[CoverageGroup]
    ) -> Dict[str, float]:
        """Compute Shannon entropy and normalized entropy for groups."""
        results = {}
        for g in groups:
            dist = g.publisher_distribution
            if not dist:
                results[g.group_id] = {"entropy": 0.0, "normalized_entropy": 0.0}
                continue
            probs = np.array(list(dist.values()), dtype=float)
            probs = probs / probs.sum()
            entropy = float(-np.sum(probs * np.log2(probs)))
            max_entropy = np.log2(len(dist)) if len(dist) > 1 else 1.0
            norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
            results[g.group_id] = {
                "entropy": round(entropy, 4),
                "normalized_entropy": round(norm_entropy, 4),
            }
        return results

