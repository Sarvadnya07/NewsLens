"""Article analysis and ML linguistic screening API routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status

from backend.api.dependencies import get_news_service
from backend.api.errors import NewsLensAPIException
from backend.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    InfluentialToken,
    MLScreeningResult,
)
from backend.schemas.common import APIResponse
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("", response_model=APIResponse[AnalysisResponse])
def analyze_article_text(
    payload: AnalysisRequest,
    service: NewsLensService = Depends(get_news_service),
):
    """Executes ML linguistic screening, related story retrieval, and fact-check matching."""
    text = payload.text.strip()
    if not text:
        raise NewsLensAPIException(
            code="EMPTY_INPUT",
            message="Analysis text cannot be empty or solely whitespace.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # 1. Linguistic ML screening
    raw_screen = service.screen_article_text(text)

    influential = [
        InfluentialToken(token=t[0], weight=t[1]) for t in raw_screen.get("influential_tokens", [])
    ]

    screening = MLScreeningResult(
        label=raw_screen.get("label", "Unknown"),
        confidence=float(raw_screen.get("confidence", 0.0)),
        score=float(raw_screen.get("score", 0.0)),
        is_uncertain=bool(raw_screen.get("is_uncertain", False)),
        explanation=raw_screen.get("explanation", ""),
        decision_threshold=float(raw_screen.get("decision_threshold", 0.5)),
        influential_tokens=influential,
    )

    # 2. Related coverage retrieval
    related = service.find_related_news(text, top_n=4)

    # 3. Accredited Fact-Check matching
    fact_checks = service.retrieve_fact_checks(text, top_k=3)

    response = AnalysisResponse(
        input_text=text,
        screening=screening,
        related_coverage=related,
        fact_check_matches=fact_checks,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return APIResponse(data=response)
