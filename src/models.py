"""Normalized data models for NewsLens India."""

import hashlib
import logging
import unicodedata
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

    if dt is None:  # defensive: every parse path above assigns or returns
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


def detect_text_language(text: str, fallback_lang: str = "en") -> str:
    """Detects text language from Unicode character scripts, respecting Indic languages.

    If Indic scripts (Devanagari, Bengali, Tamil, Telugu, etc.) are present and dominant,
    returns the appropriate language code. If Devanagari is dominant and fallback_lang is
    a recognized Devanagari language ('hi', 'mr', 'sa'), respects the declared language.
    Otherwise defaults to fallback_lang.
    """
    if not text or not isinstance(text, str):
        return fallback_lang or "en"

    counts = {"Devanagari": 0, "Bengali": 0, "Tamil": 0, "Telugu": 0, "Latin": 0}
    for ch in text:
        name = unicodedata.name(ch, "")
        if "DEVANAGARI" in name:
            counts["Devanagari"] += 1
        elif "BENGALI" in name:
            counts["Bengali"] += 1
        elif "TAMIL" in name:
            counts["Tamil"] += 1
        elif "TELUGU" in name:
            counts["Telugu"] += 1
        elif "LATIN" in name:
            counts["Latin"] += 1

    total_indic = counts["Devanagari"] + counts["Bengali"] + counts["Tamil"] + counts["Telugu"]
    if total_indic > 0 and (
        counts["Devanagari"] > counts["Latin"] or counts["Bengali"] > counts["Latin"]
    ):
        if counts["Devanagari"] >= counts["Bengali"]:
            clean_fallback = (fallback_lang or "").strip().lower()
            if clean_fallback in ("hi", "mr", "sa"):
                return clean_fallback
            return "hi"
        if counts["Bengali"] > counts["Devanagari"]:
            return "bn"

    return fallback_lang or "en"


def generate_article_id(
    canonical_url: str,
    language: Optional[str] = "en",
    source_type: Optional[str] = "rss",
    prefix: Optional[str] = None,
) -> str:
    """Generates a stable, language-aware article variant ID.

    For default English or unilingual articles, computes a 16-character SHA-256
    hash of the canonical URL (matching the canonical NewsLens schema and legacy records).
    For distinct language variants (e.g., Hindi or Marathi editions of a release or story
    sharing a URL or differing by language), binds the language code into the hash so distinct
    language representations are never discarded or collapsed.
    """
    clean_url = canonicalize_url(canonical_url)
    clean_lang = (language or "en").strip().lower()
    clean_prefix = prefix or (
        f"{source_type}_" if source_type and source_type != "newsdata" else ""
    )

    if clean_lang and clean_lang != "en":
        # Multi-language variant: bind language into hash to preserve variant identity
        digest = hashlib.sha256(f"{clean_url}:{clean_lang}".encode("utf-8")).hexdigest()[:16]
    else:
        digest = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:16]

    return f"{clean_prefix}{digest}"


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
    source_type: str  # 'gdelt', 'rss', 'newsdata', or 'manual'
    summary: Optional[str] = ""  # Optional article body snippet or description
    language: Optional[str] = "en"  # Language code
    country: Optional[str] = "IN"  # Country code
    query: Optional[str] = ""  # Search query used if any
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    origin: str = "unknown"  # 'rss', 'gdelt', 'newsdata', 'manual', or 'unknown'

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
        valid_origins = ("rss", "gdelt", "newsdata", "currents", "guardian", "manual", "unknown")
        if self.origin not in valid_origins:
            if self.source_type in valid_origins:
                self.origin = self.source_type
            else:
                self.origin = "unknown"
        elif self.origin == "unknown" and self.source_type in valid_origins:
            self.origin = self.source_type

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormalizedArticle":
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class FactCheckClaimRecord:
    """Canonical representation of an external ClaimReview evidence record."""

    id: str
    claim_text: str
    claimant: Optional[str] = None
    claim_date: Optional[str] = None
    rating_text: Optional[str] = None
    rating_standardized: Optional[str] = "unverified"
    publisher_name: str = ""
    publisher_site: Optional[str] = None
    fact_check_url: str = ""
    review_date: Optional[str] = None
    language_code: Optional[str] = "en"
    matched_article_id: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
