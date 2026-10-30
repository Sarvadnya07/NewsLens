"""Fact-check claim retrieval module using BM25Plus ranking.

Indexes verified public Indian fact-check claims from accredited watchdogs
(PIB Fact Check, BOOM Live, Alt News).
Handles single-record, empty-corpus, short, and zero-token queries safely.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Plus

from src.models import FactCheckRecord
from src.preprocessing.cleaner import tokenize_text

logger = logging.getLogger(__name__)

DEFAULT_FACT_CHECKS_PATH = "data/fact_checks.json"


class FactCheckRetriever:
    """Retrieval engine for accredited fact-check claims using BM25Plus ranking."""

    def __init__(self, data_path: str = DEFAULT_FACT_CHECKS_PATH):
        self.data_path = data_path
        self.records: List[FactCheckRecord] = []
        self.corpus_tokens: List[List[str]] = []
        self.corpus_vocab: set = set()
        self.bm25: Optional[BM25Plus] = None
        self._load_records()

    def _load_records(self):
        if not os.path.exists(self.data_path):
            logger.warning("Fact check data file not found at %s", self.data_path)
            self.records = []
            self.corpus_tokens = []
            self.corpus_vocab = set()
            self.bm25 = None
            return

        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)

            valid_records = []
            valid_tokens = []
            for item in raw_items:
                try:
                    rec = FactCheckRecord(
                        claim_id=str(item.get("claim_id", "")),
                        claim=str(item.get("claim", "")),
                        verdict=str(item.get("verdict", "")),
                        claimant=str(item.get("claimant", "")),
                        fact_checker=str(item.get("fact_checker", "")),
                        review_date=str(item.get("review_date", "")),
                        source_url=str(item.get("source_url", "")),
                        explanation=str(item.get("explanation", "")),
                    )
                    tokens = tokenize_text(f"{rec.claim} {rec.explanation} {rec.claimant}")
                    if not tokens:
                        # Fallback token if text yielded zero tokens
                        tokens = [rec.claim_id or "claim"]
                    valid_records.append(rec)
                    valid_tokens.append(tokens)
                except Exception as ex:
                    logger.warning("Skipping invalid fact check record: %s", str(ex))

            self.records = valid_records
            self.corpus_tokens = valid_tokens
            self.corpus_vocab = {tok for doc in valid_tokens for tok in doc}

            if self.corpus_tokens:
                self.bm25 = BM25Plus(self.corpus_tokens)
                logger.info("Indexed %d fact-check records into BM25Plus.", len(self.records))
            else:
                self.bm25 = None
        except Exception as e:
            logger.error("Failed to load fact-check corpus: %s", str(e))
            self.records = []
            self.corpus_tokens = []
            self.corpus_vocab = set()
            self.bm25 = None

    @property
    def total_records(self) -> int:
        return len(self.records)

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 1.0) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant fact check records for a query string.
        Returns empty list if no genuine matches meet the relevance threshold.
        """
        if not query or not isinstance(query, str) or not query.strip():
            return []

        if not self.bm25 or not self.records:
            return []

        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        # Prevent out-of-vocabulary false matches: query must have lexical overlap with corpus
        if not any(token in self.corpus_vocab for token in query_tokens):
            return []

        try:
            scores = self.bm25.get_scores(query_tokens)
        except Exception as e:
            logger.warning("BM25 score calculation failed: %s", str(e))
            return []

        scored_pairs = []
        for i, score in enumerate(scores):
            if score >= min_score:
                scored_pairs.append((score, self.records[i]))

        scored_pairs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, rec in scored_pairs[:top_k]:
            data = rec.to_dict()
            data["relevance_score"] = round(float(score), 3)
            # Add explicit advisory
            data["match_advisory"] = (
                "Note: A search match indicates similarity between the query and an investigated claim. "
                "It does not automatically verify that the queried article is identical."
            )
            results.append(data)

        return results
