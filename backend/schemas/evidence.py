"""Pydantic schemas for Evidence Retrieval and Fact-Check matching."""

from typing import List, Optional

from pydantic import BaseModel, Field


class FactCheckItem(BaseModel):
    claim_id: str
    claim: str
    verdict: str
    claimant: str
    fact_checker: str
    review_date: str
    source_url: str
    explanation: str
    similarity_score: Optional[float] = 0.0


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(5, ge=1, le=20)


class EvidenceSearchResponse(BaseModel):
    query: str
    matches: List[FactCheckItem]
    total_matches: int
