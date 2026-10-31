"""Evaluation metrics for NewsLens India hybrid evidence retrieval.

Implements standard ranking metrics with deterministic, small-fixture
suitable implementations:

    * Precision@K
    * Recall@K
    * Mean Reciprocal Rank (MRR)
    * Normalized Discounted Cumulative Gain (nDCG)

All implementations are pure functions over explicit lists of (query_id,
predicted_ranked_items, ground_truth_relevant_items) so they can be tested
against hand-computed fixtures.
"""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

# Default confidence level for bootstrap reporting
DEFAULT_CONFIDENCE = 0.95
DEFAULT_BOOTSTRAP_RESAMPLES = 2000


def _is_relevant(item: Any, relevant_set: Set[Any]) -> bool:
    """Determine whether a retrieved item matches a ground-truth relevant item."""
    if item is None:
        return False
    if hasattr(item, "id") and hasattr(item, "claim_id"):
        return item.id == relevant_set or item.claim_id in relevant_set
    if isinstance(item, (str, int)):
        return item in relevant_set
    return str(item) in {str(r) for r in relevant_set}


def precision_at_k(
    ranked: Sequence[Any], relevant_set: Set[Any], k: int
) -> float:
    """Fraction of top-k predictions that are relevant."""
    if k <= 0:
        return 0.0
    top_k = list(ranked)[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for item in top_k if _is_relevant(item, relevant_set))
    return hits / float(k)


def recall_at_k(
    ranked: Sequence[Any], relevant_set: Set[Any], k: int
) -> float:
    """Fraction of relevant items that appear in top-k."""
    if not relevant_set:
        return 0.0
    top_k = list(ranked)[:k]
    hits = sum(1 for item in top_k if _is_relevant(item, relevant_set))
    return hits / float(len(relevant_set))


def mean_reciprocal_rank(ranked: Sequence[Any], relevant_set: Set[Any]) -> float:
    """MRR: reciprocal of the rank of the first relevant item."""
    for i, item in enumerate(ranked):
        if _is_relevant(item, relevant_set):
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    ranked: Sequence[Any], relevant_set: Set[Any], k: int
) -> float:
    """Normalized DCG at rank k (binary relevance)."""
    if k <= 0:
        return 0.0
    if not relevant_set:
        return 0.0
    dcg = 0.0
    for i, item in enumerate(ranked[:k]):
        if _is_relevant(item, relevant_set):
            dcg += 1.0 / _log2(i + 2)  # position 1 -> log2(2), position 2 -> log2(3)
    ideal_hits = min(len(relevant_set), k)
    idcg = sum(1.0 / _log2(i + 2) for i in range(1, ideal_hits + 1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def _log2(x: float) -> float:
    """Return base-2 logarithm (no numpy dependency needed for tests)."""
    import math

    return math.log2(x)


def bootstrap_metric_ci(
    per_query_scores: Sequence[float],
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """Bootstrap confidence interval over per-query metric scores.

    Resamples the per-query distribution (non-parametric, stratified by
    query) and returns the point estimate, lower and upper bounds.
    """
    import numpy as np

    if not per_query_scores:
        return 0.0, 0.0, 0.0

    values = np.array(per_query_scores, dtype=float)
    point_est = float(np.mean(values))
    rng = np.random.default_rng(seed)

    n = len(values)
    boot_samples = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        sample_idx = rng.integers(0, n, size=n)
        boot_samples[i] = float(np.mean(values[sample_idx]))

    boot_samples.sort()
    alpha = 1.0 - confidence
    lower_idx = int(n_resamples * alpha / 2)
    upper_idx = int(n_resamples * (1.0 - alpha / 2))
    lower = float(boot_samples[lower_idx])
    upper = float(boot_samples[upper_idx])
    return point_est, lower, upper
