"""Authoritative provider and publication registry for NewsLens India.

Centralizes all provider configurations, categories, and operational roles:
- Configured / Enabled RSS feeds (syndicated continuous monitoring)
- Official Government RSS (PIB)
- Regional Indian RSS (ABP Live, Amar Ujala)
- Configured / Enabled GDELT API (on-demand and scheduled topic monitoring)
- Configured / Enabled NewsData.io (multi-profile quota-governed aggregation)
- Configured / Enabled Currents API (international and Indian news discovery)
- Configured / Enabled The Guardian Open Platform (first-party world reporting)
- Configured / Enabled Google Fact Check Tools API (ClaimReview evidence search)
- Documented Backlog Providers (NYT, Brave Search)
- Retired providers (preserved in datastore history, excluded from active health metrics)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ProviderDescriptor:
    """Canonical metadata definition for an ingestion source, aggregator, or evidence API."""

    id: str
    name: str
    source_type: (
        str  # 'rss' | 'gdelt' | 'newsdata' | 'currents' | 'guardian' | 'factcheck' | 'search'
    )
    endpoint_url: str
    domain: str
    is_active: bool = True  # False for retired or unimplemented backlog feeds
    is_on_demand: bool = False  # True for query-driven APIs
    category: str = "National"  # "National" | "Regional" | "Official Government" | "Global Aggregator" | "First-Party Publisher" | "Fact-Check Evidence"
    language: str = "en"
    requires_api_key: bool = False
    env_key_name: Optional[str] = None
    env_enabled_name: Optional[str] = None
    documentation_url: Optional[str] = None
    terms_url: Optional[str] = None
    supported_geographies: Tuple[str, ...] = ("india",)
    supported_profiles: Tuple[str, ...] = ("default",)


CANONICAL_GDELT_NAME = "GDELT 2.0 Doc API"
CANONICAL_GDELT_ID = "gdelt_doc_api"

CANONICAL_NEWSDATA_NAME = "NewsData.io"
CANONICAL_NEWSDATA_ID = "newsdata_io"

CANONICAL_CURRENTS_NAME = "Currents API"
CANONICAL_CURRENTS_ID = "currents"

CANONICAL_GUARDIAN_NAME = "The Guardian Open Platform"
CANONICAL_GUARDIAN_ID = "guardian_open_platform"

CANONICAL_FACTCHECK_NAME = "Google Fact Check Tools API"
CANONICAL_FACTCHECK_ID = "google_fact_check"

# Central canonical provider definitions
PROVIDER_REGISTRY: Dict[str, ProviderDescriptor] = {
    # -------------------------------------------------------------
    # 6 Active Indian National English RSS Feeds
    # -------------------------------------------------------------
    "toi_national": ProviderDescriptor(
        id="toi_national",
        name="The Times of India (National)",
        source_type="rss",
        endpoint_url="https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        domain="timesofindia.indiatimes.com",
        is_active=True,
        is_on_demand=False,
        category="National",
        language="en",
        documentation_url="https://timesofindia.indiatimes.com/rss.cms",
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
        language="en",
        documentation_url="https://www.thehindu.com/rssFeeds/",
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
        language="en",
        documentation_url="https://www.ndtv.com/rss",
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
        language="en",
        documentation_url="https://indianexpress.com/syndication/",
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
        language="en",
        documentation_url="https://www.hindustantimes.com/rss",
    ),
    "livemint_economy": ProviderDescriptor(
        id="livemint_economy",
        name="Livemint (National & Economy)",
        source_type="rss",
        endpoint_url="https://www.livemint.com/rss/news",
        domain="livemint.com",
        is_active=True,
        is_on_demand=False,
        category="National",
        language="en",
        documentation_url="https://www.livemint.com/rss",
    ),
    # -------------------------------------------------------------
    # Official Government Feeds: Press Information Bureau (PIB)
    # -------------------------------------------------------------
    "pib_english": ProviderDescriptor(
        id="pib_english",
        name="Press Information Bureau (English)",
        source_type="rss",
        endpoint_url="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3",
        domain="pib.gov.in",
        is_active=True,
        is_on_demand=False,
        category="Official Government",
        language="en",
        env_enabled_name="PIB_ENABLED",
        documentation_url="https://pib.gov.in/RssMain.aspx",
    ),
    "pib_hindi": ProviderDescriptor(
        id="pib_hindi",
        name="Press Information Bureau (Hindi)",
        source_type="rss",
        endpoint_url="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=2&Regid=3",
        domain="pib.gov.in",
        is_active=True,
        is_on_demand=False,
        category="Official Government",
        language="hi",
        env_enabled_name="PIB_ENABLED",
        documentation_url="https://pib.gov.in/RssMain.aspx",
    ),
    "pib_marathi": ProviderDescriptor(
        id="pib_marathi",
        name="Press Information Bureau (Marathi)",
        source_type="rss",
        endpoint_url="https://pib.gov.in/RssMain.aspx?ModId=6&Lang=7&Regid=3",
        domain="pib.gov.in",
        is_active=True,
        is_on_demand=False,
        category="Official Government",
        language="mr",
        env_enabled_name="PIB_ENABLED",
        documentation_url="https://pib.gov.in/RssMain.aspx",
    ),
    # -------------------------------------------------------------
    # Regional Vernacular Feeds: ABP Live & Amar Ujala
    # -------------------------------------------------------------
    "abp_english": ProviderDescriptor(
        id="abp_english",
        name="ABP Live (English)",
        source_type="rss",
        endpoint_url="https://news.abplive.com/news/india/feed",
        domain="news.abplive.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="en",
        env_enabled_name="ABP_RSS_ENABLED",
        documentation_url="https://news.abplive.com",
    ),
    "abp_hindi": ProviderDescriptor(
        id="abp_hindi",
        name="ABP News (Hindi)",
        source_type="rss",
        endpoint_url="https://www.abplive.com/news/india/feed",
        domain="abplive.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="hi",
        env_enabled_name="ABP_RSS_ENABLED",
        documentation_url="https://www.abplive.com",
    ),
    "abp_marathi": ProviderDescriptor(
        id="abp_marathi",
        name="ABP Majha (Marathi)",
        source_type="rss",
        endpoint_url="https://marathi.abplive.com/home/feed",
        domain="marathi.abplive.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="mr",
        env_enabled_name="ABP_RSS_ENABLED",
        documentation_url="https://marathi.abplive.com",
    ),
    "abp_bengali": ProviderDescriptor(
        id="abp_bengali",
        name="ABP Ananda (Bengali)",
        source_type="rss",
        endpoint_url="https://bengali.abplive.com/home/feed",
        domain="bengali.abplive.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="bn",
        env_enabled_name="ABP_RSS_ENABLED",
        documentation_url="https://bengali.abplive.com",
    ),
    "amar_ujala_breaking": ProviderDescriptor(
        id="amar_ujala_breaking",
        name="Amar Ujala (Breaking Hindi)",
        source_type="rss",
        endpoint_url="https://www.amarujala.com/rss/breaking-news.xml",
        domain="amarujala.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="hi",
        env_enabled_name="AMAR_UJALA_RSS_ENABLED",
        documentation_url="https://www.amarujala.com/rss",
    ),
    "amar_ujala_up": ProviderDescriptor(
        id="amar_ujala_up",
        name="Amar Ujala (Uttar Pradesh Hindi)",
        source_type="rss",
        endpoint_url="https://www.amarujala.com/rss/uttar-pradesh.xml",
        domain="amarujala.com",
        is_active=True,
        is_on_demand=False,
        category="Regional",
        language="hi",
        env_enabled_name="AMAR_UJALA_RSS_ENABLED",
        documentation_url="https://www.amarujala.com/rss",
    ),
    # -------------------------------------------------------------
    # Global & Multi-source Aggregators
    # -------------------------------------------------------------
    CANONICAL_GDELT_ID: ProviderDescriptor(
        id=CANONICAL_GDELT_ID,
        name=CANONICAL_GDELT_NAME,
        source_type="gdelt",
        endpoint_url="https://api.gdeltproject.org/api/v2/doc/doc",
        domain="gdeltproject.org",
        is_active=True,
        is_on_demand=True,
        category="Global Aggregator",
        language="en",
        env_enabled_name="GDELT_ENABLED",
        documentation_url="https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
    ),
    CANONICAL_NEWSDATA_ID: ProviderDescriptor(
        id=CANONICAL_NEWSDATA_ID,
        name=CANONICAL_NEWSDATA_NAME,
        source_type="newsdata",
        endpoint_url="https://newsdata.io/api/1/latest",
        domain="newsdata.io",
        is_active=True,
        is_on_demand=True,
        category="Global Aggregator",
        language="en",
        requires_api_key=True,
        env_key_name="NEWSDATA_API_KEY",
        env_enabled_name="NEWSDATA_ENABLED",
        documentation_url="https://newsdata.io/docs",
        terms_url="https://newsdata.io/terms-of-service",
        supported_profiles=("india_publishers", "global_latest", "india_global_coverage"),
    ),
    CANONICAL_CURRENTS_ID: ProviderDescriptor(
        id=CANONICAL_CURRENTS_ID,
        name=CANONICAL_CURRENTS_NAME,
        source_type="currents",
        endpoint_url="https://api.currentsapi.services/v1/latest-news",
        domain="currentsapi.services",
        is_active=True,
        is_on_demand=True,
        category="Global Aggregator",
        language="en",
        requires_api_key=True,
        env_key_name="CURRENTS_API_KEY",
        env_enabled_name="CURRENTS_ENABLED",
        documentation_url="https://currentsapi.services/en/docs/",
        terms_url="https://currentsapi.services/en/terms",
        supported_profiles=("currents_india", "currents_global"),
    ),
    # -------------------------------------------------------------
    # First-Party Global Publishers
    # -------------------------------------------------------------
    CANONICAL_GUARDIAN_ID: ProviderDescriptor(
        id=CANONICAL_GUARDIAN_ID,
        name=CANONICAL_GUARDIAN_NAME,
        source_type="guardian",
        endpoint_url="https://content.guardianapis.com/search",
        domain="theguardian.com",
        is_active=True,
        is_on_demand=True,
        category="First-Party Publisher",
        language="en",
        requires_api_key=True,
        env_key_name="GUARDIAN_API_KEY",
        env_enabled_name="GUARDIAN_ENABLED",
        documentation_url="https://open-platform.theguardian.com/documentation/",
        terms_url="https://open-platform.theguardian.com/terms-and-conditions/",
        supported_profiles=("india_coverage", "world"),
    ),
    # -------------------------------------------------------------
    # Fact-Checking & Misinformation Evidence Services
    # -------------------------------------------------------------
    CANONICAL_FACTCHECK_ID: ProviderDescriptor(
        id=CANONICAL_FACTCHECK_ID,
        name=CANONICAL_FACTCHECK_NAME,
        source_type="factcheck",
        endpoint_url="https://factchecktools.googleapis.com/v1alpha1/claims:search",
        domain="factchecktools.googleapis.com",
        is_active=True,
        is_on_demand=True,
        category="Fact-Check Evidence",
        language="en",
        requires_api_key=True,
        env_key_name="GOOGLE_FACTCHECK_API_KEY",
        env_enabled_name="GOOGLE_FACTCHECK_ENABLED",
        documentation_url="https://developers.google.com/fact-check/tools/api",
        terms_url="https://developers.google.com/terms",
    ),
    # -------------------------------------------------------------
    # Documented Backlog Providers (Inactive / Placeholders)
    # -------------------------------------------------------------
    "nyt": ProviderDescriptor(
        id="nyt",
        name="The New York Times APIs",
        source_type="publisher",
        endpoint_url="https://api.nytimes.com/svc/search/v2/articlesearch.json",
        domain="nytimes.com",
        is_active=False,
        is_on_demand=True,
        category="First-Party Publisher",
        language="en",
        requires_api_key=True,
        env_key_name="NYT_API_KEY",
        env_enabled_name="NYT_ENABLED",
        documentation_url="https://developer.nytimes.com/apis",
    ),
    "brave_search": ProviderDescriptor(
        id="brave_search",
        name="Brave News Search API",
        source_type="search",
        endpoint_url="https://api.search.brave.com/res/v1/news/search",
        domain="brave.com",
        is_active=False,
        is_on_demand=True,
        category="Search/Discovery",
        language="en",
        requires_api_key=True,
        env_key_name="BRAVE_API_KEY",
        env_enabled_name="BRAVE_ENABLED",
        documentation_url="https://brave.com/search/api/",
    ),
    # -------------------------------------------------------------
    # Retired RSS Feeds (Historical datastore integrity)
    # -------------------------------------------------------------
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
    """Returns all registered providers including active, backlog, and retired."""
    return list(PROVIDER_REGISTRY.values())


def get_active_providers(include_extensions: bool = False) -> List[ProviderDescriptor]:
    """Returns currently active monitored and API providers.

    By default (include_extensions=False), returns the core 8 providers (6 National RSS + GDELT + NewsData)
    matching legacy ingestion contracts. When include_extensions=True, returns all active providers including
    PIB, ABP, Amar Ujala, Currents, Guardian, and Fact Check.
    """
    if include_extensions:
        return [p for p in PROVIDER_REGISTRY.values() if p.is_active]
    core_ids = {
        "toi_national",
        "the_hindu_national",
        "ndtv_india",
        "indian_express_india",
        "hindustan_times_india",
        "livemint_economy",
        CANONICAL_GDELT_ID,
        CANONICAL_NEWSDATA_ID,
    }
    return [p for p in PROVIDER_REGISTRY.values() if p.id in core_ids and p.is_active]


def get_active_rss_feeds(include_extensions: bool = False) -> List[ProviderDescriptor]:
    """Returns active configured RSS feeds.

    By default (include_extensions=False), returns the 6 national English feeds for backward compatibility.
    When include_extensions=True, returns all active regional and government feeds as well.
    """
    if include_extensions:
        return [p for p in PROVIDER_REGISTRY.values() if p.is_active and p.source_type == "rss"]
    core_rss_ids = {
        "toi_national",
        "the_hindu_national",
        "ndtv_india",
        "indian_express_india",
        "hindustan_times_india",
        "livemint_economy",
    }
    return [p for p in PROVIDER_REGISTRY.values() if p.id in core_rss_ids and p.is_active]


def get_gdelt_provider() -> ProviderDescriptor:
    """Returns the canonical GDELT provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_GDELT_ID]


def get_newsdata_provider() -> ProviderDescriptor:
    """Returns the canonical NewsData.io provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_NEWSDATA_ID]


def get_currents_provider() -> ProviderDescriptor:
    """Returns the canonical Currents API provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_CURRENTS_ID]


def get_guardian_provider() -> ProviderDescriptor:
    """Returns the canonical The Guardian Open Platform provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_GUARDIAN_ID]


def get_factcheck_provider() -> ProviderDescriptor:
    """Returns the canonical Google Fact Check Tools API provider descriptor."""
    return PROVIDER_REGISTRY[CANONICAL_FACTCHECK_ID]


def get_retired_providers() -> List[ProviderDescriptor]:
    """Returns retired providers excluded from operational health."""
    return [p for p in PROVIDER_REGISTRY.values() if not p.is_active and "deccan" in p.id]


def get_provider_by_id(provider_id: str) -> Optional[ProviderDescriptor]:
    """Finds provider descriptor matching canonical ID."""
    return PROVIDER_REGISTRY.get(provider_id)


def get_provider_by_name(name: str) -> Optional[ProviderDescriptor]:
    """Finds provider descriptor matching display name."""
    for p in PROVIDER_REGISTRY.values():
        if p.name == name:
            return p
    return None
