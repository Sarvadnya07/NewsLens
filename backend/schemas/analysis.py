"""Pydantic schemas for ML Analysis and Linguistic Screening."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    text: str = Field(
        ..., min_length=10, max_length=10000, description="Article headline or content to screen"
    )
    title: Optional[str] = Field(None, max_length=500)


class InfluentialToken(BaseModel):
    token: str
    weight: str


class MLScreeningResult(BaseModel):
    label: str
    confidence: float
    score: float
    is_uncertain: bool
    explanation: str
    decision_threshold: float = 0.5
    influential_tokens: List[InfluentialToken] = []


class RelatedCoverageItem(BaseModel):
    title: str
    publisher: str
    url: str
    published_at: Optional[str] = None
    similarity: float
    relationship: str
    is_syndication: bool = False


class EvidenceAssessment(BaseModel):
    available_evidence: List[str] = []
    missing_evidence: List[str] = []
    analytical_recommendations: str = ""


class AnalysisResponse(BaseModel):
    input_text: str
    screening: MLScreeningResult
    related_coverage: List[RelatedCoverageItem] = []
    fact_check_matches: List[Dict[str, Any]] = []
    evidence_assessment: Optional[EvidenceAssessment] = None
    analysis_timestamp: str
