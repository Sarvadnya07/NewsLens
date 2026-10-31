"""Service layer for hybrid evidence retrieval.

Provides a clean, repository-style contract used by the Streamlit UI pages.
Wraps HybridFactCheckRetriever and re-exposes its results as the standard
NewsLens evidence-list format.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.models import FactCheckRecord
from src.retrieval.hybrid_retrieval import HybridFactCheckRetriever, RetrievalCandidate
from src.retrieval.fact_check import FactCheckRetriever

logger = logging.getLogger(__name__)


class RetrievalService:
    """Unified retrieval service: dual-backed BM25Plus + TF-IDF + RRF."""

    def __init__(
        self,
        fact_checks_path: str = "data/fact_checks.json",
        top_k: int = 20,
        rrf_k: float = 60.0,
    ):
        self.top_k = top_k
        self.rrf_k = rrf_k
        self._hybrid: Optional[HybridFactCheckRetriever] = None
        self._legacy: Optional[FactCheckRetriever] = None
        self._load(fact_checks_path)

    def _load(self, fact_checks_path: str) -> None:
        """Load the fact-check archive once and build both retrievers."""
        raw = FactCheckRetriever(data_path=fact_checks_path)
        self._legacy = raw
        self._hybrid = HybridFactCheckRetriever(
            records=raw.records,
            top_k=self.top_k,
            rrf_k=self.rrf_k,
        )
        logger.info(
            "Retrieval service initialised with %d fact-check records.",
            len(raw.records),
        )

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """Run hybrid retrieval and return a standard evidence list."""
        candidates = self._hybrid.retrieve(query, top_k=top_k or self.top_k)
        return [c.to_dict() for c in candidates]

    def retrieve_candidates(self, query: str, top_k: Optional[int] = None) -> List[RetrievalCandidate]:
        """Return typed candidate objects for consumers that need detail."""
        return self._hybrid.retrieve(query, top_k=top_k or self.top_k)

    @property
    def total_records(self) -> int:
        return self._hybrid.total_records if self._hybrid else 0

    @property
    def corpus_version(self) -> int:
        return self._hybrid._corpus_version if self._hybrid else 0

    def rebuild_indexes(self) -> None:
        """Re-index the underlying corpus (e.g. after an archive update)."""
        if self._hybrid:
            self._hybrid.rebuild()
            logger.info("Hybrid retrieval indexes rebuilt.")
