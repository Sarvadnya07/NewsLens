"""Normalized data models for NewsLens India."""

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any


@dataclass
class NormalizedArticle:
    """Canonical representation of an ingested news article across all sources."""
    id: str                         # Unique hash or slug
    title: str                      # Headline
    url: str                        # Original URL
    publisher: str                  # Publisher or domain name
    published_at: str               # ISO formatted or raw publication timestamp
    ingested_at: str                # ISO timestamp of when NewsLens fetched it
    source_type: str                # 'gdelt', 'rss', or 'manual'
    summary: Optional[str] = ""     # Optional article body snippet or description
    language: Optional[str] = "en"  # Language code
    country: Optional[str] = "IN"   # Country code
    query: Optional[str] = ""       # Search query used if any
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedArticle":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class FactCheckRecord:
    """Canonical representation of a verified fact check claim."""
    claim_id: str
    claim: str
    verdict: str                    # e.g., 'False', 'Misleading', 'True', 'Manipulated Media'
    claimant: str                   # Person, group, or rumor origin
    fact_checker: str               # e.g., 'PIB Fact Check', 'BoomLive', 'AltNews'
    review_date: str
    source_url: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
