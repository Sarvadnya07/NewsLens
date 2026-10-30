"""Duplicate and related-news detection for NewsLens India.

Identifies:
1. Exact or near-identical duplicate headlines across publishers.
2. Thematic / related coverage using character/word n-gram TF-IDF cosine similarity.
Preserves all original publisher attributions and source URLs.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import NormalizedArticle
from src.preprocessing.cleaner import clean_text


class NewsDeduplicator:
    """Clustering and relationship discovery engine for news articles."""

    def __init__(self, similarity_threshold: float = 0.55):
        self.similarity_threshold = similarity_threshold

    def find_related_and_duplicates(
        self,
        articles: List[NormalizedArticle]
    ) -> List[Dict[str, Any]]:
        """
        Groups articles into coverage clusters based on headline similarity.
        Returns a list of cluster dicts:
        {
            "primary_article": NormalizedArticle,
            "related_articles": List[{"article": NormalizedArticle, "similarity": float}],
            "publishers": List[str],
            "total_coverage_count": int
        }
        """
        if not articles:
            return []

        if len(articles) == 1:
            return [{
                "primary_article": articles[0],
                "related_articles": [],
                "publishers": [articles[0].publisher],
                "total_coverage_count": 1
            }]

        cleaned_titles = [clean_text(a.title) for a in articles]

        # Use unigram + bigram TF-IDF
        try:
            vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
            tfidf_matrix = vectorizer.fit_transform(cleaned_titles)
            sim_matrix = cosine_similarity(tfidf_matrix)
        except Exception:
            # Fallback if vocabulary is degenerate
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
                    if sim >= self.similarity_threshold:
                        visited.add(j)
                        related.append({
                            "article": articles[j],
                            "similarity": round(sim, 3)
                        })
                        publishers.add(articles[j].publisher)

            # Sort related articles by similarity score
            related.sort(key=lambda x: x["similarity"], reverse=True)

            clusters.append({
                "primary_article": primary,
                "related_articles": related,
                "publishers": list(publishers),
                "total_coverage_count": 1 + len(related)
            })

        return clusters

    def find_related_to_query(
        self,
        query_text: str,
        articles: List[NormalizedArticle],
        top_n: int = 5,
        min_sim: float = 0.25
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
                results.append({
                    "article": articles[i],
                    "similarity": round(float(score), 3)
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_n]
