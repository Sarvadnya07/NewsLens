"""Article analysis and ML linguistic screening API routes."""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status

from backend.api.dependencies import get_news_service
from backend.api.errors import NewsLensAPIException
from backend.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    EvidenceAssessment,
    InfluentialToken,
    MLScreeningResult,
    RelatedCoverageItem,
)
from backend.schemas.common import APIResponse
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _generate_evidence_assessment(
    screening: MLScreeningResult,
    related_items: List[RelatedCoverageItem],
    fact_checks: List[Dict[str, Any]],
) -> EvidenceAssessment:
    available: List[str] = []
    missing: List[str] = []

    # 1. Available Evidence
    if fact_checks:
        for fc in fact_checks[:3]:
            checker = fc.get("fact_checker", "Accredited Fact-Checker")
            verdict = fc.get("verdict", "Investigated")
            claim = fc.get("claim", "")
            available.append(
                f"Accredited fact-check by {checker}: rated '{verdict}' on claim \"{claim}\"."
            )

    unique_publishers = list(dict.fromkeys(r.publisher for r in related_items if r.publisher))
    syndicated_items = [r for r in related_items if r.is_syndication]
    independent_items = [r for r in related_items if not r.is_syndication]

    if independent_items:
        pub_list = ", ".join(list(dict.fromkeys(r.publisher for r in independent_items))[:3])
        available.append(
            f"Independent reporting indexed from {len(independent_items)} distinct coverage article(s) across publishers ({pub_list})."
        )

    if syndicated_items:
        available.append(
            f"Wire republication / syndication pattern: {len(syndicated_items)} source(s) share identical or verbatim agency copy."
        )

    if not available:
        available.append(
            "No direct accredited fact-checks or existing publisher wire articles matching this query were found in the current local archive."
        )

    # 2. Missing Evidence & Data Gaps
    if not fact_checks:
        missing.append(
            "No indexed records from accredited Indian fact-checking watchdogs (PIB Fact Check, BOOM Live, Alt News) match this specific submission."
        )

    if len(unique_publishers) < 2:
        missing.append(
            "Lack of multi-source corroboration: Fewer than 2 distinct newsrooms have verified and published independent reporting on this topic."
        )

    if screening.is_uncertain:
        missing.append(
            "Linguistic ML screening confidence is marginal or vocabulary is out-of-distribution; statistical patterns alone cannot substantiate veracity."
        )

    missing.append(
        "Primary source documentation (official government gazette notification, signed ministry circular, or registered court filing) is not linked in the input text."
    )

    # 3. Analytical Recommendation
    if fact_checks and any(
        str(fc.get("verdict", "")).lower() in ("fake", "false", "misleading", "fabricated")
        for fc in fact_checks
    ):
        top_fc = fact_checks[0]
        rec = (
            f"High caution: Close match with an accredited fact-check from {top_fc.get('fact_checker', 'IFCN')} "
            f"with verdict '{top_fc.get('verdict', 'Investigated')}'. Review official findings before secondary syndication or dissemination."
        )
    elif independent_items and len(unique_publishers) >= 2:
        rec = (
            f"Corroborating coverage detected across {len(unique_publishers)} publishers. "
            "Examine differences in headline framing and verify attribution to primary sources or named spokespersons."
        )
    else:
        rec = (
            "Independent editorial cross-verification required. Consult accredited press agency wire releases, "
            "official government portals (e.g. Press Information Bureau pib.gov.in), or authorized institutional statements before citing."
        )

    return EvidenceAssessment(
        available_evidence=available,
        missing_evidence=missing,
        analytical_recommendations=rec,
    )


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

    token_list = raw_screen.get("influential_tokens") or raw_screen.get("tokens", [])
    influential = [
        InfluentialToken(token=t[0], weight=str(t[1]))
        for t in token_list
        if isinstance(t, (list, tuple)) and len(t) >= 2
    ]

    raw_score = raw_screen.get("score")
    if raw_score is None:
        raw_score = raw_screen.get("model_score", 0.0)
    screening_score = float(0.0 if raw_score is None else raw_score)
    screening_explanation = raw_screen.get("explanation") or raw_screen.get("uncertainty_note", "")

    screening = MLScreeningResult(
        label=raw_screen.get("label", "Unknown"),
        confidence=float(raw_screen.get("confidence", 0.0)),
        score=screening_score,
        is_uncertain=bool(raw_screen.get("is_uncertain", False)),
        explanation=screening_explanation,
        decision_threshold=float(raw_screen.get("decision_threshold", 0.5)),
        influential_tokens=influential,
    )

    # 2. Related coverage retrieval (bounded to maximum 10 unique articles)
    raw_related = service.find_related_news(text, top_n=10)
    formatted_related: List[RelatedCoverageItem] = []
    seen_urls = set()

    for item in raw_related:
        art = item.get("article")
        if not art:
            continue
        art_url = getattr(art, "url", "")
        if art_url in seen_urls:
            continue
        seen_urls.add(art_url)

        sim = float(item.get("similarity", 0.0))
        rel_type = str(item.get("relationship", "similar_coverage"))
        # Decouple duplicate identity from independent corroboration
        is_synd = rel_type in ("exact_or_republished", "likely_syndicated") or sim >= 0.85

        pub_time = getattr(art, "published_at", None)
        pub_time_str = (
            pub_time.isoformat()
            if pub_time is not None and hasattr(pub_time, "isoformat")
            else str(pub_time)
            if pub_time
            else None
        )

        formatted_related.append(
            RelatedCoverageItem(
                title=getattr(art, "title", "Untitled Article"),
                publisher=getattr(art, "publisher", "Unknown Publisher"),
                url=art_url,
                published_at=pub_time_str,
                similarity=sim,
                relationship=rel_type,
                is_syndication=is_synd,
            )
        )
        if len(formatted_related) >= 10:
            break

    # 3. Fact-Check archive matching (bounded to top 5)
    fact_checks = service.retrieve_fact_checks(text, top_k=5)

    # 4. Dynamic evidence assessment
    assessment = _generate_evidence_assessment(
        screening=screening,
        related_items=formatted_related,
        fact_checks=fact_checks,
    )

    response = AnalysisResponse(
        input_text=text,
        screening=screening,
        related_coverage=formatted_related,
        fact_check_matches=fact_checks,
        evidence_assessment=assessment,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return APIResponse(data=response)
