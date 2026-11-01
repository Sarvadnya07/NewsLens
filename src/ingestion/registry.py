"""Authoritative provider and publication registry for NewsLens India.

Centralizes all provider configurations, categories, and operational roles:
- Configured / Enabled RSS feeds (syndicated continuous monitoring)
- Configured / Enabled GDELT API (on-demand and scheduled topic monitoring)
- Retired providers (preserved in datastore history, excluded from active health metrics)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProviderDescriptor:
    """Canonical metadata definition for an ingestion source or external feed."""

    id: str
    name: str
    source_type: str  # 'rss' | 'gdelt'
    endpoint_url: str
    domain: str
    is_active: bool = True  # False for retired feeds
    is_on_demand: bool = False  # True for GDELT
    category: str = "National"
    language: str = "en"


CANONICAL_GDELT_NAME = "GDELT 2.0 Doc API"
CANONICAL_GDELT_ID = "gdelt_doc_api"

CANONICAL_NEWSDATA_NAME = "NewsData.io"
CANONICAL_NEWSDATA_ID = "newsdata_io"

# Central canonical provider definitions
PROVIDER_REGISTRY: Dict[str, ProviderDescriptor] = {
    # 6 Active RSS Feeds
    "toi_national": ProviderDescriptor(
        id="toi_national",
        name="The Times of India (National)",
        source_type="rss",
        endpoint_url="https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        domain="timesofindia.indiatimes.com",
        is_active=True,
        is_on_demand=False,
        category="National",
    ),
    "the_hindu_national": ProviderDescriptor(
        id="the_hindu_national",
        name="The Hindu (National)",
        source_type="rss",
        endpoint_url="https://www.thehindu.com/news/national/feeder/default.rss",
        domain="thehindu.com",
        is_active=True,
        is_on_demand=False,
        category="National",
    ),
    "ndtv_india": ProviderDescriptor(
        id="ndtv_india",
        name="NDTV (India News)",
        source_type="rss",
        endpoint_url="https://feeds.feedburner.com/ndtvnews-india-news",
        domain="ndtv.com",
        is_active=True,
        is_on_demand=False,
        category="National",
    ),
    "indian_express_india": ProviderDescriptor(
        id="indian_express_india",
        name="Indian Express (India)",
        source_type="rss",
        endpoint_url="https://indianexpress.com/section/india/feed/",
        domain="indianexpress.com",
        is_active=True,
        is_on_demand=False,
        category="National",
    ),
    "hindustan_times_india": ProviderDescriptor(
        id="hindustan_times_india",
        name="Hindustan Times (India)",
        source_type="rss",
        endpoint_url="https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        domain="hindustantimes.com",
        is_active=True,
        is_on_demand=False,
        category="National",
    ),
    "livemint_economy": ProviderDescriptor(
        id="livemint_economy",
        name="Livemint (National & Economy)",
        source_type="rss",
        endpoint_url="https://www.livemint.com/rss/news",
        domain="livemint.com",
        is_active=True,
        is_on_demand=False,
        category="Business",
    ),
    # 1 Active GDELT Provider (on-demand and scheduled topic monitoring)
    CANONICAL_GDELT_ID: ProviderDescriptor(
        id=CANONICAL_GDELT_ID,
        name=CANONICAL_GDELT_NAME,
        source_type="gdelt",
        endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc",
        domain="gdeltproject.org",
        is_active=True,
        is_on_demand=True,
        category="Global Aggregator",
    ),
    # 1 Active NewsData.io Provider (India & Global news monitoring via Latest API)
    CANONICAL_NEWSDATA_ID: ProviderDescriptor(
        id=CANONICAL_NEWSDATA_ID,
        name=CANONICAL_NEWSDATA_NAME,
        source_type="newsdata",
        endpoint_url="https://newsdata.io/api/1/latest",
        domain="newsdata.io",
        is_active=True,
        is_on_demand=True,
        category="Global & National Aggregator",
    ),
    # Retired RSS Feeds (preserved for datastore history, excluded from active monitoring health metrics)
    "deccan_herald_national": ProviderDescriptor(
        id="deccan_herald_national",
        name="Deccan Herald (National)",
        source_type="rss",
        endpoint_url="https://www.deccanherald.com/rss/national.rss",
        domain="deccanherald.com",
        is_active=False,
        is_on_demand=False,
        category="National",
    ),
}


def get_all_providers() -> List[ProviderDescriptor]:
    """Returns all registered providers including active and retired."""
    return list(PROVIDER_REGISTRY.values())


def get_active_providers() -> List[ProviderDescriptor]:
    """Returns all currently active monitored providers (6 RSS + 1 GDELT = 7 total)."""
    return [p for p in PROVIDER_REGISTRY.values() if p.is_active]


def get_active_rss_feeds() -> List[ProviderDescriptor]:
    """Returns active configured RSS feeds (6 feeds)."""
    return [p for p in PROVIDER_REGISTRY.values() if p.is_active and p.source_type == "rss"]


def get_gdelt_provider() -> ProviderDescriptor:
    """Returns the canonical GDELT provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_GDELT_ID]


def get_newsdata_provider() -> ProviderDescriptor:
    """Returns the canonical NewsData.io provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_NEWSDATA_ID]


def get_retired_providers() -> List[ProviderDescriptor]:
    """Returns retired providers excluded from operational health."""
    return [p for p in PROVIDER_REGISTRY.values() if not p.is_active]


def get_provider_by_name(name: str) -> Optional[ProviderDescriptor]:
    """Finds provider descriptor matching display name."""
    for p in PROVIDER_REGISTRY.values():
        if p.name == name:
            return p
    return None
