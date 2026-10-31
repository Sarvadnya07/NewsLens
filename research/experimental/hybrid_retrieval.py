"""Hybrid Evidence Retrieval and Relevance Ranking for NewsLens India.

Combines BM25Plus lexical ranking with TF-IDF vector-similarity ranking
using Reciprocal Rank Fusion (RRF) so that the two complementary
scoring families are merged into one defensible candidate order.

Mathematical contract
---------------------
BM25Plus (original implementation preserved):
    score(q,d) = sum_{t in q} IDF(t) * (tf(t,d) * (k1 + 1))
                      / (tf(t,d) + k1 * (1 - b + b * |d| / avgdl))

TF-IDF cosine:
    cos(v_q, v_d) = (v_q . v_d) / (||v_q|| * ||v_d||)

Reciprocal Rank Fusion (RRF):
    RRF(d) = sum_{r in R} 1 / (k + rank_r(d))

The two constituent rankings are each converted to a rank position first.
RRF(D) is then a monotone, scale-invariant combination that does not require
choosing an arbitrary score threshold or weighting the raw BM25 and cosine
outputs against one another.

Exposes:
    claim_id, title, publisher, source_url, published_at, verdict,
    bm25_rank, tfidf_rank, cosine_similarity, rrf_score,
    final_rank, match_reason, provenance
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from rank_bm25 import BM25Plus

from src.models import FactCheckRecord
from src.preprocessing.cleaner import tokenize_text

logger = logging.getLogger(__name__)

# RRF smoothing constant. 60 is the widely used default from Cormack
# et al. (2009) and is preserved here so candidate ordering remains
# independent of score scale or corpus size.
RRF_K = 60.0

# How many top candidates each constituent ranker returns before RRF.
DEFAULT_TOP_K = 20

# Provenance records where the fact-checker is not present.
UNKNOWN_PROVENANCE = "Unknown"