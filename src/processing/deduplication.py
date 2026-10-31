"""Duplicate and related-news detection for NewsLens India.

Identifies:
1. Exact or near-identical duplicate headlines across publishers.
2. Thematic / related coverage using character/word n-gram TF-IDF cosine similarity.
Classifies relationships as 'exact_duplicate', 'likely_duplicate', or 'similar_coverage'.
Preserves all original publisher attributions and source URLs.
"""

from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import NormalizedArticle
from src.preprocessing.cleaner import clean_text

# Minimum cosine similarity for a stored article to be reported as related to
# arbitrary user query text. Shared with the UI so the stated threshold and the
# applied threshold cannot drift apart.
QUERY_MIN_SIMILARITY = 0.15


class NewsDeduplicator:
    """Clustering and relationship discovery engine for news articles."""

    def __init__(self, exact_threshold: float = 0.90, similar_threshold: float = 0.55):
        self.exact_threshold = exact_threshold
        self.similar_threshold = similar_threshold

    def classify_relationship(self, sim: float) -> str:
        if sim >= self.exact_threshold:
            return "exact_or_republished"
        elif sim >= 0.70:
            return "likely_syndicated"
        elif sim >= self.similar_threshold:
            return "similar_coverage"
        return "unrelated"

    def find_related_and_duplicates(
        self, articles: List[NormalizedArticle]
    ) -> List[Dict[str, Any]]:
        """
        Groups articles into coverage clusters based on headline similarity.
        Returns a list of cluster dicts:
        {
            "primary_article": NormalizedArticle,
            "related_articles": List[{"article": NormalizedArticle, "similarity": float, "relationship": str}],
            "publishers": List[str],
            "total_coverage_count": int
        }
        """
        if not articles:
            return []

        if len(articles) == 1:
            return [
                {
                    "primary_article": articles[0],
                    "related_articles": [],
                    "publishers": [articles[0].publisher],
                    "total_coverage_count": 1,
                }
            ]

        cleaned_titles = [clean_text(a.title) for a in articles]

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            tfidf_matrix = vectorizer.fit_transform(cleaned_titles)
            sim_matrix = cosine_similarity(tfidf_matrix)
        except Exception:
            sim_matrix = np.eye(len(articles))

        visited = set()
        clusters: List[Dict[str, Any]] = []

        for i in range(len(articles)):
            if i in visited:
                continue

            visited.add(i)
            primary = articles[i]
            related = []
            publishers = {primary.publisher}

            for j in range(len(articles)):
                if i != j and j not in visited:
                    sim = float(sim_matrix[i, j])
                    if sim >= self.similar_threshold:
                        visited.add(j)
                        rel_type = self.classify_relationship(sim)
                        related.append(
                            {
                                "article": articles[j],
                                "similarity": round(sim, 3),
                                "relationship": rel_type,
                            }
                        )
                        publishers.add(articles[j].publisher)

            # Sort related articles by similarity score
            related.sort(key=lambda x: x["similarity"], reverse=True)

            clusters.append(
                {
                    "primary_article": primary,
                    "related_articles": related,
                    "publishers": list(publishers),
                    "total_coverage_count": 1 + len(related),
                }
            )

        return clusters

    def find_related_to_query(
        self,
        query_text: str,
        articles: List[NormalizedArticle],
        top_n: int = 5,
        min_sim: float = QUERY_MIN_SIMILARITY,
    ) -> List[Dict[str, Any]]:
        """Finds related articles from an article list against arbitrary user text."""
        if not query_text or not articles:
            return []

        cleaned_query = clean_text(query_text)
        cleaned_titles = [clean_text(a.title) for a in articles]

        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            all_texts = [cleaned_query] + cleaned_titles
            matrix = vectorizer.fit_transform(all_texts)
            query_vec = matrix[0:1]
            doc_vecs = matrix[1:]
            scores = cosine_similarity(query_vec, doc_vecs)[0]
        except Exception:
            return []

        results = []
        for i, score in enumerate(scores):
            if score >= min_sim:
                rel_type = self.classify_relationship(float(score))
                results.append(
                    {
                        "article": articles[i],
                        "similarity": round(float(score), 3),
                        "relationship": rel_type,
                    }
                )

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_n]
