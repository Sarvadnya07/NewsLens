"""Normalized data models for NewsLens India."""

import logging
import urllib.parse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Additional non-ISO layouts seen in publisher feeds. RFC 822 variants are
# handled by email.utils.parsedate_to_datetime before these are attempted.
_FALLBACK_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d %b %Y %H:%M:%S",
    "%d %B %Y %H:%M:%S",
)


def normalize_published_at(value: Any) -> str:
    """Returns *value* as an ISO-8601 UTC timestamp, or an empty string.

    Publication dates arrive from feeds in several shapes (ISO-8601, RFC 822,
    naive local times). Storing them verbatim made string-based sorting and
    date filtering incorrect, so every timestamp is normalized to one
    comparable, timezone-aware representation at the domain boundary.

    Unparseable values return an empty string rather than the original text:
    the raw value is never silently presented as a valid timestamp, and
    consumers fall back to ``ingested_at``.
    """
    if value is None:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return ""
        dt = None
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError):
                for fmt in _FALLBACK_DATE_FORMATS:
                    try:
                        dt = datetime.strptime(text, fmt)
                        break
                    except ValueError:
                        continue
        if dt is None:
            logger.debug("Unparseable publication date retained as metadata only: %r", text)
            return ""

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def canonicalize_url(url: str) -> str:
    """Removes standard marketing/tracking query parameters and normalizes URL."""
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return url.strip()

        tracking_keys = {
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_term",
            "utm_content",
            "fbclid",
            "gclid",
            "ref",
            "publisher",
        }
        queries = urllib.parse.parse_qsl(parsed.query)
        cleaned_queries = [
            (k, v)
            for k, v in queries
            if k.lower() not in tracking_keys and not k.lower().startswith("utm_")
        ]
        new_query = urllib.parse.urlencode(cleaned_queries)
        return urllib.parse.urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/"),
                "",
                new_query,
                "",
            )
        )
    except Exception:
        return url.strip()


@dataclass
class NormalizedArticle:
    """Canonical representation of an ingested news article across all sources."""

    id: str  # Unique hash or slug
    title: str  # Headline
    url: str  # Original canonicalized URL
    publisher: str  # Publisher or domain name
    published_at: (
        str  # ISO formatted UTC or raw publication timestamp (empty string if unavailable)
    )
    ingested_at: str  # ISO timestamp (UTC) of when NewsLens fetched it
    source_type: str  # 'gdelt', 'rss', or 'manual'
    summary: Optional[str] = ""  # Optional article body snippet or description
    language: Optional[str] = "en"  # Language code
    country: Optional[str] = "IN"  # Country code
    query: Optional[str] = ""  # Search query used if any
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.url:
            self.url = canonicalize_url(self.url)
        raw_published = self.published_at
        self.published_at = normalize_published_at(raw_published)
        if self.published_at == "" and raw_published:
            metadata = dict(self.raw_metadata or {})
            metadata.setdefault("published_at_raw", str(raw_published))
            self.raw_metadata = metadata
        if not self.ingested_at:
            self.ingested_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedArticle":
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class FactCheckRecord:
    """Canonical representation of a verified fact check claim."""

    claim_id: str
    claim: str
    verdict: str  # e.g., 'Fake', 'Misleading', 'False / Out of Context'
    claimant: str  # Person, group, or rumor origin
    fact_checker: str  # e.g., 'PIB Fact Check (India)', 'BOOM Live', 'Alt News'
    review_date: str
    source_url: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
