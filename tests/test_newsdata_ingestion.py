"""Comprehensive unit and integration tests for NewsData.io ingestion provider."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from backend.main import app
from src.ingestion.models import (
    STATUS_DISABLED,
    STATUS_INVALID_RESPONSE,
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_QUOTA_EXCEEDED,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ProviderFetchResult,
)
from src.ingestion.newsdata import (
    PROFILE_GLOBAL_LATEST,
    PROFILE_INDIA_GLOBAL_COVERAGE,
    PROFILE_INDIA_PUBLISHERS,
    NewsDataClient,
)
from src.ingestion.registry import CANONICAL_NEWSDATA_ID, CANONICAL_NEWSDATA_NAME
from src.models import NormalizedArticle
from src.services.news_service import NewsLensService
from src.storage.database import DatabaseManager

_MOCK_SUCCESSFUL_PAYLOAD = {
    "status": "success",
    "totalResults": 2,
    "results": [
        {
            "article_id": "nd_art_001",
            "title": "India Unveils Green Hydrogen Super-Hub in Gujarat",
            "link": "https://www.thehindu.com/business/green-hydrogen-hub-gujarat.html?utm_source=feed",
            "keywords": ["energy", "hydrogen", "india", "gujarat"],
            "creator": ["Special Correspondent"],
            "video_url": None,
            "description": "The Ministry of New and Renewable Energy announced the sanction of a green hydrogen facility.",
            "content": "Full article text describing the infrastructure budget and private sector consortium partners.",
            "pubDate": "2026-11-01 10:30:00",
            "pubDateTZ": "UTC",
            "image_url": "https://www.thehindu.com/images/hydrogen.jpg",
            "source_id": "thehindu",
            "source_name": "The Hindu",
            "source_url": "https://www.thehindu.com",
            "source_priority": 1,
            "country": ["in"],
            "category": ["business", "top"],
            "language": "english",
        },
        {
            "article_id": "nd_art_002",
            "title": "Global Semiconductor Alliance Expands R&D in Bengaluru",
            "link": "https://timesofindia.indiatimes.com/tech/semiconductor-bengaluru-rd.cms",
            "keywords": ["semiconductor", "bengaluru", "tech"],
            "creator": ["Tech Bureau"],
            "video_url": None,
            "description": "Major chip manufacturers establish advanced packaging research lab.",
            "content": "Details on investment and technical specifications.",
            "pubDate": "2026-11-01 11:15:00",
            "pubDateTZ": "UTC",
            "image_url": None,
            "source_id": "timesofindia",
            "source_name": "The Times of India",
            "source_url": "https://timesofindia.indiatimes.com",
            "source_priority": 1,
            "country": ["in"],
            "category": ["technology"],
            "language": "english",
        },
    ],
    "nextPage": "page_token_999",
}


def test_newsdata_client_initialization_and_configuration(monkeypatch):
    """Verify NewsDataClient configuration resolves key from argument or environment."""
    assert CANONICAL_NEWSDATA_ID == "newsdata_io"
    assert CANONICAL_NEWSDATA_NAME == "NewsData.io"

    # 1. Direct key passed
    client1 = NewsDataClient(api_key="test_direct_key")
    assert client1.is_configured is True
    assert client1.api_key == "test_direct_key"
    assert client1.base_url == "https://newsdata.io/api/1"
    assert client1.endpoint_url == "https://newsdata.io/api/1/latest"

    # 2. Key via environment variable
    monkeypatch.setenv("NEWSDATA_API_KEY", "env_secret_key_xyz")
    client2 = NewsDataClient()
    assert client2.is_configured is True
    assert client2.api_key == "env_secret_key_xyz"

    # 3. No key provided
    monkeypatch.delenv("NEWSDATA_API_KEY", raising=False)
    client3 = NewsDataClient(api_key="")
    assert client3.is_configured is False
    assert client3.api_key == ""


def test_newsdata_client_disabled_when_key_missing():
    """Verify client skips API call gracefully when no key is configured."""
    client = NewsDataClient(api_key="")
    with patch("requests.get") as mock_get:
        res = client.fetch_articles()
        assert not mock_get.called

    assert res.source_id == CANONICAL_NEWSDATA_ID
    assert res.source_name == CANONICAL_NEWSDATA_NAME
    assert res.status == STATUS_DISABLED
    assert res.items_count == 0
    assert len(res.articles) == 0
    assert "not configured" in res.error_message


def test_newsdata_client_fetch_success_and_normalization():
    """Verify successful NewsData.io response normalization conforming to canonical contracts."""
    client = NewsDataClient(api_key="secret_test_key_123")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _MOCK_SUCCESSFUL_PAYLOAD

    with patch("requests.get", return_value=mock_resp) as mock_get:
        res = client.fetch_articles(query="hydrogen", country="in", language="en")

    assert mock_get.called
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs["headers"]["X-ACCESS-KEY"] == "secret_test_key_123"
    assert "User-Agent" in call_kwargs["headers"]
    assert call_kwargs["params"]["q"] == "hydrogen"
    assert call_kwargs["params"]["country"] == "in"

    assert res.status == STATUS_SUCCESS
    assert res.items_count == 2
    assert len(res.articles) == 2

    art1 = res.articles[0]
    assert "Green Hydrogen" in art1.title
    assert art1.publisher == "The Hindu"
    assert art1.source_type == "newsdata"
    assert art1.origin == "newsdata"
    assert art1.country == "IN"
    assert art1.language == "en"
    assert "utm_source" not in art1.url
    assert art1.published_at.startswith("2026-11-01")
    assert art1.raw_metadata.get("article_id") == "nd_art_001"
    assert art1.raw_metadata.get("discovery_profile") == PROFILE_INDIA_PUBLISHERS
    assert art1.raw_metadata.get("publisher_country") == "IN"


def test_three_discovery_profiles_parameter_and_metadata_isolation():
    """Verify three distinct discovery profiles correctly isolate queries and metadata."""
    client = NewsDataClient(api_key="test_key_abc")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "success",
        "totalResults": 1,
        "results": [
            {
                "article_id": "art_intl_1",
                "title": "Reuters: Global Markets Review Indian Tech Sector",
                "link": "https://www.reuters.com/markets/india-tech-review",
                "source_name": "Reuters",
                "country": ["us"],
                "language": "english",
                "pubDate": "2026-11-01 14:00:00",
            }
        ],
    }

    # Profile 1: india_publishers (must include country='in')
    with patch("requests.get", return_value=mock_resp) as mock_get:
        client.fetch_profile(PROFILE_INDIA_PUBLISHERS)
        p1_params = mock_get.call_args[1]["params"]
        assert p1_params.get("country") == "in"

    # Profile 2: global_latest (must NOT restrict country to 'in')
    with patch("requests.get", return_value=mock_resp) as mock_get:
        res2 = client.fetch_profile(PROFILE_GLOBAL_LATEST)
        p2_params = mock_get.call_args[1]["params"]
        assert "country" not in p2_params or p2_params.get("country") != "in"
        assert res2.articles[0].raw_metadata.get("discovery_profile") == PROFILE_GLOBAL_LATEST
        assert res2.articles[0].raw_metadata.get("publisher_country") == "US"
        assert res2.articles[0].raw_metadata.get("discovery_scope") == "global_discovery"
        assert res2.articles[0].raw_metadata.get("discovery_subject") == "general"
        assert res2.articles[0].raw_metadata.get("story_geography") is None

    # Profile 3: india_global_coverage (searches for India while explicitly excluding Indian newsrooms)
    with patch("requests.get", return_value=mock_resp) as mock_get:
        res3 = client.fetch_profile(PROFILE_INDIA_GLOBAL_COVERAGE)
        p3_params = mock_get.call_args[1]["params"]
        assert p3_params.get("q") == "India"
        assert p3_params.get("excludecountry") == "in"
        assert "country" not in p3_params
        assert (
            res3.articles[0].raw_metadata.get("discovery_profile") == PROFILE_INDIA_GLOBAL_COVERAGE
        )
        assert res3.articles[0].raw_metadata.get("discovery_scope") == "international_on_india"
        assert res3.articles[0].raw_metadata.get("discovery_subject") == "india_search"
        assert res3.articles[0].raw_metadata.get("publisher_country") == "US"
        assert res3.articles[0].raw_metadata.get("story_geography") is None

    # Unknown publisher country case: verify country is None / not fabricated
    mock_resp_no_country = MagicMock()
    mock_resp_no_country.status_code = 200
    mock_resp_no_country.json.return_value = {
        "status": "success",
        "totalResults": 1,
        "results": [
            {
                "article_id": "art_no_country",
                "title": "Global Market Volatility Report",
                "link": "https://unknown-publisher.org/news/1",
                "pubDate": "2026-11-01 12:00:00",
            }
        ],
    }
    with patch("requests.get", return_value=mock_resp_no_country):
        res_no_country = client.fetch_profile(PROFILE_GLOBAL_LATEST)
        art = res_no_country.articles[0]
        assert art.country is None
        assert art.raw_metadata.get("publisher_country") is None
        assert art.raw_metadata.get("story_geography") is None


def test_newsdata_client_empty_results():
    """Verify 200 response with empty results returns STATUS_NO_RESULTS."""
    client = NewsDataClient(api_key="test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success", "totalResults": 0, "results": []}

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles()

    assert res.status == STATUS_NO_RESULTS
    assert res.items_count == 0
    assert len(res.articles) == 0


def test_newsdata_client_rate_limiting_429():
    """Verify HTTP 429 response classifies as STATUS_RATE_LIMITED without exposing secrets."""
    client = NewsDataClient(api_key="secret_key_val")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.json.return_value = {
        "status": "error",
        "results": {"message": "Rate limit exceeded", "code": "RateLimitExceeded"},
    }

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles()

    assert res.status == STATUS_RATE_LIMITED
    assert res.http_status == 429
    assert "rate limit" in res.error_message.lower()
    assert "secret_key_val" not in res.error_message


def test_newsdata_client_auth_failure_401_403():
    """Verify HTTP 401 / 403 classifies as provider_unavailable without leaking keys."""
    client = NewsDataClient(api_key="invalid_or_expired_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 401

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles()

    assert res.status == STATUS_PROVIDER_UNAVAILABLE
    assert res.http_status == 401
    assert "authentication failed" in res.error_message.lower()
    assert "invalid_or_expired_key" not in res.error_message


def test_newsdata_client_timeout_and_retries():
    """Verify connection timeouts classify as STATUS_TIMEOUT with retries."""
    client = NewsDataClient(
        api_key="test_key",
        max_retries=1,
        retry_delay_seconds=0.01,
    )

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Read timeout")):
        res = client.fetch_articles()

    assert res.status == STATUS_TIMEOUT
    assert "timed out" in res.error_message.lower()


def test_newsdata_client_invalid_json():
    """Verify HTML or invalid payload classifies as STATUS_INVALID_RESPONSE."""
    client = NewsDataClient(api_key="test_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles()

    assert res.status == STATUS_INVALID_RESPONSE
    assert "not valid json" in res.error_message.lower()


def test_quota_governance_budget_enforcement_and_logging(tmp_path: Path):
    """Verify proactive quota governor enforces daily and 15-min limits and logs requests."""
    test_db = str(tmp_path / "quota_test.db")
    db = DatabaseManager(db_path=test_db)

    # Initialize client with strict 2-request daily budget and 2-request 15m budget
    client = NewsDataClient(
        api_key="budget_test_key",
        db=db,
        daily_budget=2,
        rolling_15m_budget=2,
        min_interval_seconds=0.0,
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "success",
        "totalResults": 1,
        "results": [{"article_id": "a1", "title": "Headline 1", "link": "https://example.com/1"}],
    }

    with patch("requests.get", return_value=mock_resp) as mock_get:
        # Request 1: succeeds
        res1 = client.fetch_profile(PROFILE_INDIA_PUBLISHERS)
        assert res1.status == STATUS_SUCCESS

        # Request 2: succeeds
        res2 = client.fetch_profile(PROFILE_INDIA_PUBLISHERS)
        assert res2.status == STATUS_SUCCESS

        # Request 3: blocked by quota governor before HTTP call!
        res3 = client.fetch_profile(PROFILE_INDIA_PUBLISHERS)
        assert res3.status == STATUS_QUOTA_EXCEEDED
        assert "budget reached" in res3.error_message.lower()
        # Ensure only 2 external calls were made
        assert mock_get.call_count == 2

    # Verify quota telemetry
    telemetry = db.get_provider_quota_telemetry(
        CANONICAL_NEWSDATA_ID, daily_budget=2, rolling_15m_budget=2
    )
    assert telemetry["daily_requests_used"] == 2
    assert telemetry["is_exhausted"] is True


def test_pagination_continuation_and_cycle_guard():
    """Verify pagination loop requests subsequent pages and terminates on token cycles."""
    client = NewsDataClient(api_key="test_key", max_pages_per_run=3)

    page1_payload = {
        "status": "success",
        "totalResults": 2,
        "results": [
            {"article_id": "p1_1", "title": "Page 1 News", "link": "https://example.com/p1"}
        ],
        "nextPage": "token_page_2",
    }
    # Page 2 returns the same token again (cycle/bug simulation)
    page2_payload = {
        "status": "success",
        "totalResults": 2,
        "results": [
            {"article_id": "p2_1", "title": "Page 2 News", "link": "https://example.com/p2"}
        ],
        "nextPage": "token_page_2",
    }

    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = page1_payload

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = page2_payload

    with patch("requests.get", side_effect=[mock_resp1, mock_resp2, mock_resp2]) as mock_get:
        res = client.fetch_profile(PROFILE_INDIA_PUBLISHERS, max_pages=3)

    # Must fetch page 1 and page 2, then stop due to cycle guard (avoiding unbounded loop)
    assert mock_get.call_count == 2
    assert res.items_count == 2
    assert res.articles[0].title == "Page 1 News"
    assert res.articles[1].title == "Page 2 News"


def test_multi_provider_provenance_and_discoveries_table(tmp_path: Path):
    """Verify article_discoveries preserves multi-provider discovery events for the same article."""
    test_db = str(tmp_path / "provenance_test.db")
    service = NewsLensService(db_path=test_db)

    now = "2026-11-01T12:00:00+00:00"
    canonical_url = "https://www.reuters.com/world/india/renewable-targets-2026"

    # Discovery Event 1: First discovered via GDELT
    gdelt_article = NormalizedArticle(
        id="art_reuters_001",
        title="India Meets Renewable Targets Ahead of Schedule",
        url=canonical_url,
        publisher="Reuters",
        published_at=now,
        ingested_at=now,
        source_type="gdelt",
        origin="gdelt",
        raw_metadata={"discovery_profile": "gdelt_search"},
    )
    service.db.upsert_article(gdelt_article)

    # Discovery Event 2: Subsequently discovered via NewsData.io (global_latest)
    newsdata_article = NormalizedArticle(
        id="art_reuters_001",
        title="India Meets Renewable Targets Ahead of Schedule",
        url=canonical_url,
        publisher="Reuters",
        published_at=now,
        ingested_at=now,
        source_type="newsdata",
        origin="newsdata",
        raw_metadata={"article_id": "nd_9988", "discovery_profile": PROFILE_GLOBAL_LATEST},
    )
    service.db.upsert_article(newsdata_article)

    # 1. Stored articles table retains single canonical row (idempotent, no duplicate rows)
    articles = service.db.get_articles()
    assert len(articles) == 1

    # 2. article_discoveries table records BOTH discovery events with full provenance
    discoveries = service.db.get_article_discoveries("art_reuters_001")
    assert len(discoveries) == 2

    d1, d2 = discoveries[0], discoveries[1]
    assert d1["provider_id"] == "gdelt_doc_api"
    assert d2["provider_id"] == "newsdata_io"
    assert d2["discovery_profile"] == PROFILE_GLOBAL_LATEST
    assert d2["provider_article_id"] == "nd_9988"

    # 3. Repeated identical ingestion of NewsData article is idempotent
    service.db.upsert_article(newsdata_article)
    discoveries_repeat = service.db.get_article_discoveries("art_reuters_001")
    assert len(discoveries_repeat) == 2

    # 4. Multi-provider discoveries do NOT inflate publisher counts or clustering corroboration
    publishers_dist = service.db.get_publishers_distribution()
    assert publishers_dist.get("Reuters") == 1
    clusters = service.deduplicator.find_related_and_duplicates(articles)
    assert len(clusters) == 1
    assert clusters[0]["publishers"] == ["Reuters"]


def test_safe_upstream_connectivity_diagnostic():
    """Verify upstream connectivity diagnostic checks authentication safely without leaking keys."""
    client = NewsDataClient(api_key="")
    # 1. Blocked when key missing
    res_blocked = client.test_upstream_connectivity()
    assert res_blocked["status"] == "BLOCKED"
    assert res_blocked["authenticated"] is False

    # 2. Mocked successful authentication
    client_live = NewsDataClient(api_key="real_key_mocked")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success", "totalResults": 100}

    with patch("requests.get", return_value=mock_resp):
        res_ok = client_live.test_upstream_connectivity()

    assert res_ok["status"] == "SUCCESS"
    assert res_ok["authenticated"] is True
    assert "real_key_mocked" not in str(res_ok)


def test_service_refresh_newsdata_persistence_and_cache(tmp_path: Path):
    """Verify NewsLensService persists NewsData.io articles with origin='newsdata' and updates telemetry."""
    test_db = str(tmp_path / "newsdata_service.db")
    service = NewsLensService(db_path=test_db)

    now = "2026-11-01T12:00:00+00:00"
    mock_articles = [
        NormalizedArticle(
            id="nd_test_001",
            title="India Launches Mission Space Station",
            url="https://isro.gov.in/news/space-station",
            publisher="ISRO News",
            published_at=now,
            ingested_at=now,
            source_type="newsdata",
            origin="newsdata",
        ),
        NormalizedArticle(
            id="nd_test_002",
            title="Reserve Bank of India Monetary Policy Review",
            url="https://rbi.org.in/news/policy-2026",
            publisher="Reserve Bank of India",
            published_at=now,
            ingested_at=now,
            source_type="newsdata",
            origin="newsdata",
        ),
    ]

    mock_fetch_res = ProviderFetchResult(
        source_id=CANONICAL_NEWSDATA_ID,
        source_name=CANONICAL_NEWSDATA_NAME,
        source_type="newsdata",
        status=STATUS_SUCCESS,
        articles=mock_articles,
        items_count=2,
        duration_ms=210.0,
        http_status=200,
    )

    with patch.object(service.newsdata, "fetch_profile", return_value=mock_fetch_res):
        fetch_res = service.refresh_newsdata(profile=PROFILE_INDIA_PUBLISHERS)

    assert fetch_res.status == STATUS_SUCCESS
    assert fetch_res.new_items_inserted == 2

    stored = service.db.get_articles(source_type="newsdata")
    assert len(stored) == 2
    for art in stored:
        assert art.source_type == "newsdata"
        assert art.origin == "newsdata"

    st = service.db.get_source_status(CANONICAL_NEWSDATA_NAME)
    assert st is not None
    assert st["source_name"] == CANONICAL_NEWSDATA_NAME
    assert st["source_type"] == "newsdata"
    assert st["status"] == STATUS_SUCCESS
    assert st["last_http_status"] == 200
    assert st["items_fetched"] == 2


def test_service_refresh_all_includes_newsdata_when_configured(tmp_path: Path):
    """Verify refresh_all coordinates RSS, GDELT, and NewsData when key is configured."""
    test_db = str(tmp_path / "refresh_all_nd.db")
    service = NewsLensService(db_path=test_db)
    service.newsdata.api_key = "active_test_key"

    mock_rss_res = MagicMock()
    mock_rss_res.total_fetched = 5
    mock_rss_res.new_stored = 5
    mock_rss_res.provider_results = {}

    mock_gdelt_res = ProviderFetchResult(
        source_id="gdelt_doc_api",
        source_name="GDELT 2.0 Doc API",
        source_type="gdelt",
        status=STATUS_SUCCESS,
        items_count=3,
        new_items_inserted=3,
    )

    mock_nd_res = ProviderFetchResult(
        source_id=CANONICAL_NEWSDATA_ID,
        source_name=CANONICAL_NEWSDATA_NAME,
        source_type="newsdata",
        status=STATUS_SUCCESS,
        items_count=4,
        new_items_inserted=4,
    )

    with (
        patch.object(service, "refresh_rss_feeds", return_value=mock_rss_res),
        patch.object(service, "refresh_gdelt", return_value=mock_gdelt_res),
        patch.object(service, "refresh_newsdata", return_value=mock_nd_res),
    ):
        result = service.refresh_all(gdelt_query="India", newsdata_query="India")

    assert CANONICAL_NEWSDATA_NAME in result.provider_results
    assert result.total_fetched == 12
    assert result.new_stored == 12
    assert result.all_succeeded is True


def test_fastapi_refresh_newsdata_endpoint():
    """Verify FastAPI /api/v1/ingestion/refresh accepts source_type='newsdata' and profile."""
    client = TestClient(app)

    mock_nd_res = ProviderFetchResult(
        source_id=CANONICAL_NEWSDATA_ID,
        source_name=CANONICAL_NEWSDATA_NAME,
        source_type="newsdata",
        status=STATUS_SUCCESS,
        items_count=6,
        duration_ms=180.0,
        http_status=200,
        new_items_inserted=6,
    )

    with patch(
        "src.services.news_service.NewsLensService.refresh_newsdata", return_value=mock_nd_res
    ):
        res = client.post(
            "/api/v1/ingestion/refresh",
            json={"source_type": "newsdata", "profile": PROFILE_GLOBAL_LATEST, "max_pages": 1},
        )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["success"] is True
    assert data["total_fetched"] == 6
    assert data["new_stored"] == 6
    assert data["discovery_profile"] == PROFILE_GLOBAL_LATEST
    assert CANONICAL_NEWSDATA_NAME in data["summary"]


def test_multi_worker_atomic_quota_reservation_and_failure_refund(tmp_path: Path):
    """Verify atomic SQLite reservation across workers, process restart persistence, and failure refunds."""
    test_db = str(tmp_path / "multi_worker_test.db")
    db = DatabaseManager(db_path=test_db)

    # 1. Concurrent reservations across workers:
    # Set strict budget of 3 daily requests. 10 workers simultaneously attempt reservation.
    def worker_reserve(worker_id: int):
        return db.reserve_provider_budget(
            provider_id=CANONICAL_NEWSDATA_ID,
            profile=f"worker_{worker_id}",
            daily_budget=3,
            rolling_15m_budget=3,
            min_interval_seconds=0.0,
            credits=1,
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(worker_reserve, range(10)))

    successful = [r for r in results if r[0] is True]
    rejected = [r for r in results if r[0] is False]

    # Exactly 3 workers reserved budget; 7 were rejected
    assert len(successful) == 3
    assert len(rejected) == 7

    # 2. Conservative accounting on ambiguous failure vs pre-dispatch cancel:
    res1_id = successful[0][2]
    # Ambiguous transmission failure (timeout/500): conservatively billed as consumed (1 credit)
    db.finalize_provider_request(
        reservation_id=res1_id,
        status_code=504,
        outcome="timeout",
        latency_ms=12000.0,
    )
    # Slot is NOT refunded because request was dispatched
    blocked, _, _ = db.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="worker_retry_after_timeout",
        daily_budget=3,
        rolling_15m_budget=3,
        min_interval_seconds=0.0,
        credits=1,
    )
    assert blocked is False

    # Undispatched / pre-flight cancellation: refunded with outcome='canceled'
    res2_id = successful[1][2]
    db.finalize_provider_request(
        reservation_id=res2_id,
        status_code=None,
        outcome="canceled",
        credits_consumed=0,
    )
    # Now slot is refunded!
    allowed, reason, new_res_id = db.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="worker_retry_after_cancel",
        daily_budget=3,
        rolling_15m_budget=3,
        min_interval_seconds=0.0,
        credits=1,
    )
    assert allowed is True
    assert new_res_id is not None

    # 3. Process restart persistence:
    # A new DatabaseManager instance connects to the same SQLite datastore
    db_restarted = DatabaseManager(db_path=test_db)
    telemetry = db_restarted.get_provider_quota_telemetry(
        provider_id=CANONICAL_NEWSDATA_ID,
        daily_budget=3,
        rolling_15m_budget=3,
    )
    # 3 active credits are reserved/used
    assert telemetry["daily_requests_used"] == 3
    assert telemetry["is_exhausted"] is True

    # 4. Refresh interval enforcement:
    # Reserve for a profile with a 60s minimum interval
    db.finalize_provider_request(
        reservation_id=new_res_id,
        status_code=200,
        outcome="success",
        latency_ms=120.0,
        credits_consumed=1,
    )
    # Profile "worker_retry_after_cancel" was just executed; attempt immediate second call with 60s interval
    blocked_interval, interval_msg, _ = db.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="worker_retry_after_cancel",
        daily_budget=10,
        rolling_15m_budget=10,
        min_interval_seconds=60.0,
        credits=1,
    )
    assert blocked_interval is False
    assert "Minimum interval between worker_retry_after_cancel refreshes not elapsed" in (
        interval_msg or ""
    )


def _mp_worker_reserve_proc(db_path: str, worker_id: int, result_queue: Any) -> None:
    """Worker process running in independent OS process space using its own SQLite connection."""
    from src.ingestion.registry import CANONICAL_NEWSDATA_ID
    from src.storage.database import DatabaseManager

    db = DatabaseManager(db_path=db_path)
    allowed, reason, res_id = db.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile=f"proc_{worker_id}",
        daily_budget=3,
        rolling_15m_budget=3,
        min_interval_seconds=0.0,
        credits=1,
    )
    result_queue.put((worker_id, allowed, reason, res_id))


def _mp_worker_abandon_proc(db_path: str, ready_queue: Any) -> None:
    """Worker in a separate process that reserves a slot and then hangs until killed."""
    import time

    from src.ingestion.registry import CANONICAL_NEWSDATA_ID
    from src.storage.database import DatabaseManager

    db = DatabaseManager(db_path=db_path)
    allowed, reason, res_id = db.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="abandoned_proc",
        daily_budget=1,
        rolling_15m_budget=1,
        min_interval_seconds=0.0,
        credits=1,
    )
    ready_queue.put((allowed, res_id))
    if allowed:
        time.sleep(30)


def test_multiprocess_quota_coordination_and_abandoned_recovery(tmp_path: Path):
    """Verify quota coordination across independent OS processes and recovery from abandoned processes."""
    import multiprocessing as mp
    import sqlite3
    from datetime import datetime, timedelta, timezone

    ctx = mp.get_context("spawn")
    test_db = str(tmp_path / "mp_quota_test.db")
    DatabaseManager(db_path=test_db)  # Initialize database schema

    # 1. Spawn 6 separate Python processes competing for 3 budget slots
    result_queue = ctx.Queue()
    processes = [
        ctx.Process(target=_mp_worker_reserve_proc, args=(test_db, i, result_queue))
        for i in range(6)
    ]
    for p in processes:
        p.start()
    for p in processes:
        p.join(timeout=10)

    results = []
    while not result_queue.empty():
        results.append(result_queue.get())

    assert len(results) == 6
    successful_procs = [r for r in results if r[1] is True]
    blocked_procs = [r for r in results if r[1] is False]

    # Exactly 3 independent processes won budget slots; 3 were rejected
    assert len(successful_procs) == 3
    assert len(blocked_procs) == 3

    # 2. Abandoned process recovery test:
    # A worker process reserves a slot and is killed abruptly (SIGTERM / terminate)
    abandon_db = str(tmp_path / "abandon_quota_test.db")
    db_ab = DatabaseManager(db_path=abandon_db)
    ready_q = ctx.Queue()
    p_abandon = ctx.Process(target=_mp_worker_abandon_proc, args=(abandon_db, ready_q))
    p_abandon.start()
    allowed_ab, res_id = ready_q.get(timeout=5)
    assert allowed_ab is True

    # Terminate the worker process abruptly
    p_abandon.terminate()
    p_abandon.join(timeout=5)

    # While reservation lease is active (within 300s), budget remains locked against new workers
    blocked_while_leased, _, _ = db_ab.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="recovery_worker",
        daily_budget=1,
        rolling_15m_budget=1,
        min_interval_seconds=0.0,
        credits=1,
    )
    assert blocked_while_leased is False

    # Simulate lease expiry by backdating the abandoned reservation past 300 seconds
    stale_iso = (datetime.now(timezone.utc) - timedelta(seconds=305)).isoformat()
    with sqlite3.connect(abandon_db) as conn:
        conn.execute(
            "UPDATE provider_request_log SET requested_at = ? WHERE id = ?", (stale_iso, res_id)
        )
        conn.commit()

    # Once the lease has expired, a new worker process cleanly recovers and reserves the budget
    allowed_after_expiry, _, new_id = db_ab.reserve_provider_budget(
        provider_id=CANONICAL_NEWSDATA_ID,
        profile="recovery_worker",
        daily_budget=1,
        rolling_15m_budget=1,
        min_interval_seconds=0.0,
        credits=1,
    )
    assert allowed_after_expiry is True
    assert new_id is not None


def test_build_newsdata_query_validation():
    """Verify mutual exclusivity and length restrictions for NewsData.io query parameters."""
    from src.ingestion.newsdata import build_newsdata_query

    # Valid single query
    res = build_newsdata_query(q="technology AND AI")
    assert res == {"q": "technology AND AI"}

    # Valid qInTitle
    res_title = build_newsdata_query(q_in_title="ISRO satellite launch")
    assert res_title == {"qInTitle": "ISRO satellite launch"}

    # Valid qInMeta
    res_meta = build_newsdata_query(q_in_meta="renewable energy")
    assert res_meta == {"qInMeta": "renewable energy"}

    # Mutually exclusive violation
    with pytest.raises(ValueError, match="allows only one search mode at a time"):
        build_newsdata_query(q="technology", q_in_title="space")

    # Length violation (> 512 chars)
    long_query = "keyword " * 75
    with pytest.raises(ValueError, match="exceeds maximum allowed length"):
        build_newsdata_query(q=long_query)


def test_newsdata_extended_metadata_and_country_mapping(tmp_path: Path):
    """Verify that extended metadata (ai_tag, sentiment, image_url) and country ISO codes are normalized."""
    client = NewsDataClient(api_key="test_key")

    mock_raw_item = {
        "article_id": "nd_test_12345",
        "title": "Indian Aerospace Advances Rapidly",
        "link": "https://example.com/aerospace-report-101",
        "description": "Report on aerospace development in Bangalore.",
        "content": "Expanded content about satellite propulsion.",
        "creator": ["Dr. K. Sharma"],
        "keywords": ["aerospace", "satellites", "ISRO"],
        "pubDate": "2026-11-02 04:00:00",
        "country": ["india"],
        "language": "hi",
        "category": ["technology"],
        "image_url": "https://example.com/images/rocket.jpg",
        "video_url": "https://example.com/videos/launch.mp4",
        "sentiment": "positive",
        "sentiment_stats": {"positive": 80.0, "neutral": 15.0, "negative": 5.0},
        "ai_tag": ["aerospace", "satellites"],
        "ai_region": ["Bangalore"],
        "ai_org": ["ISRO"],
        "ai_summary": "Summary of recent Indian aerospace test results.",
        "duplicate": False,
        "source_name": "Bangalore Chronicle",
        "source_id": "bangalore_chronicle",
    }

    articles = client._normalize_items(
        raw_items=[mock_raw_item],
        discovery_profile="india_publishers",
        query_used="aerospace",
    )

    assert len(articles) == 1
    art = articles[0]
    assert art.country == "IN"  # Mapped from full name 'india' to ISO 2-letter 'IN'
    assert art.language == "hi"
    assert art.raw_metadata["image_url"] == "https://example.com/images/rocket.jpg"
    assert art.raw_metadata["video_url"] == "https://example.com/videos/launch.mp4"
    assert art.raw_metadata["sentiment"] == "positive"
    assert art.raw_metadata["ai_tag"] == ["aerospace", "satellites"]
    assert art.raw_metadata["ai_region"] == ["Bangalore"]
    assert art.raw_metadata["ai_org"] == ["ISRO"]
