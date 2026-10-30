"""Fact-check claim retrieval module using BM25Okapi ranking.

Reuses the Rank-BM25 algorithmic framework from research/rank_bm25
over verified public Indian fact-check records.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Plus, BM25Okapi

from src.models import FactCheckRecord
from src.preprocessing.cleaner import tokenize_text

logger = logging.getLogger(__name__)

DEFAULT_FACT_CHECKS_PATH = "data/fact_checks.json"


class FactCheckRetriever:
    """Retrieval engine for accredited fact-check claims using BM25 ranking."""

    def __init__(self, data_path: str = DEFAULT_FACT_CHECKS_PATH):
        self.data_path = data_path
        self.records: List[FactCheckRecord] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load_records()

    def _load_records(self):
        if not os.path.exists(self.data_path):
            logger.warning("Fact check data file not found at %s", self.data_path)
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)

            self.records = [FactCheckRecord(**item) for item in raw_items]
            # Build tokenized corpus: combine claim + explanation for rich lexical matching
            self.corpus_tokens = [
                tokenize_text(f"{r.claim} {r.explanation} {r.claimant}")
                for r in self.records
            ]
            if self.corpus_tokens and any(self.corpus_tokens):
                self.bm25 = BM25Plus(self.corpus_tokens)
                logger.info("Indexed %d fact-check records into BM25Plus.", len(self.records))
        except Exception as e:
            logger.error("Failed to load fact-check corpus: %s", str(e))
            self.records = []
            self.corpus_tokens = []
            self.bm25 = None

    @property
    def total_records(self) -> int:
        return len(self.records)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant fact check records for a query string.
        Returns empty list if no genuine matches meet the relevance threshold.
        """
        if not query or not query.strip() or not self.bm25 or not self.records:
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Pair records with scores
        scored_pairs = []
        for i, score in enumerate(scores):
            if score >= min_score:
                scored_pairs.append((score, self.records[i]))

        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, rec in scored_pairs[:top_k]:
            data = rec.to_dict()
            data["relevance_score"] = round(float(score), 3)
            results.append(data)

        return results
