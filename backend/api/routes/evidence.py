"""Evidence retrieval and ClaimReview matching API routes."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_news_service
from backend.schemas.common import APIResponse
from backend.schemas.evidence import (
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    FactCheckItem,
)
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("/search", response_model=APIResponse[EvidenceSearchResponse])
def search_evidence(
    payload: EvidenceSearchRequest,
    service: NewsLensService = Depends(get_news_service),
):
    """Retrieves archived fact-check claims using BM25Plus ranking algorithm."""
    raw_results = service.retrieve_fact_checks(query=payload.query, top_k=payload.top_k)

    items = []
    for r in raw_results:
        # Check if record is nested or flat dict
        rec = r.get("record", r) if isinstance(r.get("record"), dict) else r
        score = float(r.get("relevance_score", r.get("similarity_score", 0.0)))
        items.append(
            FactCheckItem(
                claim_id=str(rec.get("claim_id", "")),
                claim=str(rec.get("claim", "")),
                verdict=str(rec.get("verdict", "")),
                claimant=str(rec.get("claimant", "")),
                fact_checker=str(rec.get("fact_checker", "")),
                review_date=str(rec.get("review_date", "")),
                source_url=str(rec.get("source_url", "")),
                explanation=str(rec.get("explanation", "")),
                similarity_score=score,
            )
        )

    return APIResponse(
        data=EvidenceSearchResponse(
            query=payload.query,
            matches=items,
            total_matches=len(items),
        )
    )
