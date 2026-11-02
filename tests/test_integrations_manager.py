"""Comprehensive tests for the Central API Integration Management System.

Tests cover:
- Centralized configuration and secret redaction
- Provider registry metadata and lookup
- Currents API client (normal fetch, quota enforcement, error classification)
- The Guardian Open Platform client (fetch, rate limiting, normalization)
- Google Fact Check Tools API client (ClaimReview parsing, persistence)
- FastAPI /api/v1/integrations endpoints (overview, single provider, testing, refresh)
- Secret non-disclosure across API responses
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.config import Settings, redact_secret, sanitize_text
from backend.main import app
from src.ingestion.currents import CurrentsClient
from src.ingestion.factcheck import GoogleFactCheckClient
from src.ingestion.guardian import GuardianClient
from src.ingestion.models import (
    STATUS_DISABLED,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
)
from src.ingestion.registry import (
    CANONICAL_CURRENTS_ID,
    CANONICAL_FACTCHECK_ID,
    CANONICAL_GDELT_ID,
    CANONICAL_GUARDIAN_ID,
    CANONICAL_NEWSDATA_ID,
    PROVIDER_REGISTRY,
    get_active_rss_feeds,
    get_all_providers,
)
from src.storage.database import DatabaseManager

# --------------------------------------------------------------------------
# Configuration & Secret Redaction Tests
# --------------------------------------------------------------------------


def test_secret_redaction_and_sanitization():
    assert redact_secret(None) == "[Not Configured]"
    assert redact_secret("") == "[Not Configured]"
    assert redact_secret("short") == "***"
    assert redact_secret("abcdef123456") == "abc...456"

    # Sanitize URL params and bearer tokens
    raw_log = "Error connecting to https://api.example.com?key=supersecret123&user=42"
    clean_log = sanitize_text(raw_log)
    assert "supersecret123" not in clean_log
    assert "[REDACTED]" in clean_log

    auth_log = "Header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    clean_auth = sanitize_text(auth_log)
    assert "Bearer [REDACTED]" in clean_auth


def test_pydantic_settings_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "NewsLens India API"
    assert s.INTEGRATION_REQUEST_TIMEOUT == 20.0
    assert hasattr(s, "NEWSDATA_ENABLED")
    assert hasattr(s, "CURRENTS_ENABLED")
    assert hasattr(s, "GUARDIAN_ENABLED")
    assert hasattr(s, "GOOGLE_FACTCHECK_ENABLED")


# --------------------------------------------------------------------------
# Provider Registry Metadata Tests
# --------------------------------------------------------------------------


def test_provider_registry_completeness():
    all_p = get_all_providers()
    assert len(all_p) >= 20

    rss_feeds = get_active_rss_feeds(include_extensions=True)
    # 6 National + 3 PIB + 4 ABP + 2 Amar Ujala = 15 RSS feeds
    assert len(rss_feeds) >= 15

    # Core backward compatible feeds
    core_rss = get_active_rss_feeds(include_extensions=False)
    assert len(core_rss) == 6

    # Check key providers
    assert CANONICAL_NEWSDATA_ID in PROVIDER_REGISTRY
    assert CANONICAL_CURRENTS_ID in PROVIDER_REGISTRY
    assert CANONICAL_GUARDIAN_ID in PROVIDER_REGISTRY
    assert CANONICAL_FACTCHECK_ID in PROVIDER_REGISTRY
    assert CANONICAL_GDELT_ID in PROVIDER_REGISTRY

    # Ensure required metadata
    guardian_desc = PROVIDER_REGISTRY[CANONICAL_GUARDIAN_ID]
    assert guardian_desc.requires_api_key is True
    assert guardian_desc.env_key_name == "GUARDIAN_API_KEY"
    assert "india_coverage" in guardian_desc.supported_profiles


# --------------------------------------------------------------------------
# Currents API Client Tests
# --------------------------------------------------------------------------


def test_currents_client_disabled_or_unconfigured():
    with patch("backend.config.settings.CURRENTS_API_KEY", None):
        client = CurrentsClient(api_key=None)
        assert client.is_configured is False
        res = client.fetch_profile("currents_india")
        assert res.status == STATUS_DISABLED

        # Test connection when unconfigured
        t_res = client.test_connection()
        assert t_res["success"] is False
        assert t_res["status"] == "not_configured"


@patch("src.ingestion.currents.requests.get")
def test_currents_client_fetch_success(mock_get, isolated_test_db):
    db = DatabaseManager(db_path=isolated_test_db)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "ok",
        "news": [
            {
                "id": "curr_101",
                "title": "Indian Aerospace Advances",
                "description": "ISRO announces next generation launch vehicle.",
                "url": "https://example.com/aerospace/isro-launch",
                "author": "Science Reporter",
                "image": "https://example.com/image.jpg",
                "language": "en",
                "category": ["science", "india"],
                "published": "2026-11-01 10:00:00 +0000",
            }
        ],
    }
    mock_get.return_value = mock_resp

    with patch("backend.config.settings.CURRENTS_ENABLED", True):
        client = CurrentsClient(api_key="mock_currents_key", db=db)
        res = client.fetch_profile("currents_india")

        assert res.status == STATUS_SUCCESS
        assert res.items_count == 1
        art = res.articles[0]
        assert art.title == "Indian Aerospace Advances"
        assert art.source_type == "currents"
        assert art.origin == "currents"
        assert art.country == "IN"


@patch("src.ingestion.currents.requests.get")
def test_currents_client_rate_limited(mock_get, isolated_test_db):
    db = DatabaseManager(db_path=isolated_test_db)
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_get.return_value = mock_resp

    with patch("backend.config.settings.CURRENTS_ENABLED", True):
        client = CurrentsClient(api_key="mock_currents_key", db=db)
        res = client.fetch_profile("currents_india")
        assert res.status == STATUS_RATE_LIMITED
        assert res.items_count == 0


# --------------------------------------------------------------------------
# The Guardian Open Platform Client Tests
# --------------------------------------------------------------------------


def test_guardian_client_unconfigured():
    client = GuardianClient(api_key=None)
    assert client.is_configured is False
    res = client.fetch_profile("india_coverage")
    assert res.status == STATUS_DISABLED


@patch("src.ingestion.guardian.requests.get")
def test_guardian_client_fetch_success(mock_get, isolated_test_db):
    db = DatabaseManager(db_path=isolated_test_db)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "response": {
            "status": "ok",
            "results": [
                {
                    "id": "world/2026/nov/01/india-solar-transition",
                    "sectionId": "world",
                    "sectionName": "World news",
                    "webPublicationDate": "2026-11-01T14:30:00Z",
                    "webTitle": "India expands clean power grid to rural communities",
                    "webUrl": "https://www.theguardian.com/world/2026/nov/01/india-solar-transition",
                    "fields": {
                        "headline": "India expands clean power grid",
                        "standfirst": "Renewable energy milestone reached in southern states.",
                        "byline": "Hannah Ellis-Petersen",
                        "thumbnail": "https://media.guim.co.uk/sample.jpg",
                    },
                }
            ],
        }
    }
    mock_get.return_value = mock_resp

    with patch("backend.config.settings.GUARDIAN_ENABLED", True):
        client = GuardianClient(api_key="mock_guardian_key", db=db)
        res = client.fetch_profile("india_coverage")

        assert res.status == STATUS_SUCCESS
        assert res.items_count == 1
        art = res.articles[0]
        assert "Hannah Ellis-Petersen" in art.publisher
        assert art.country == "GB"
        assert art.source_type == "guardian"
        assert art.origin == "guardian"


# --------------------------------------------------------------------------
# Google Fact Check Tools API Client Tests
# --------------------------------------------------------------------------


@patch("src.ingestion.factcheck.requests.get")
def test_google_factcheck_search_and_persist(mock_get, isolated_test_db):
    db = DatabaseManager(db_path=isolated_test_db)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "claims": [
            {
                "text": "Viral image claims RBI released 5000 rupee notes.",
                "claimant": "WhatsApp Forward",
                "claimDate": "2026-10-25T00:00:00Z",
                "claimReview": [
                    {
                        "publisher": {
                            "name": "BOOM Live",
                            "site": "boomlive.in",
                        },
                        "url": "https://www.boomlive.in/fact-check/rbi-5000-note-fake-news",
                        "title": "No, RBI has not announced Rs 5000 currency note",
                        "reviewDate": "2026-10-26T00:00:00Z",
                        "textualRating": "False",
                        "languageCode": "en",
                    }
                ],
            }
        ]
    }
    mock_get.return_value = mock_resp

    client = GoogleFactCheckClient(api_key="mock_google_key", db=db)
    claims = client.search_claims(query="5000 rupee note")

    assert len(claims) == 1
    rec = claims[0]
    assert rec.publisher_name == "BOOM Live"
    assert rec.rating_standardized == "false"
    assert "boomlive.in" in rec.fact_check_url

    # Verify persisted in database table
    with db._connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, rating_text, rating_standardized FROM fact_check_claims WHERE id=?",
            (rec.id,),
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "False"
        assert row[2] == "false"


# --------------------------------------------------------------------------
# FastAPI Integration Management Endpoint Tests
# --------------------------------------------------------------------------


def test_api_integrations_overview():
    client = TestClient(app)
    resp = client.get("/api/v1/integrations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert data["total_registered"] >= 20
    assert "providers" in data
    assert any(p["id"] == "toi_national" for p in data["providers"])
    assert any(p["id"] == "currents" for p in data["providers"])
    assert any(p["id"] == "guardian_open_platform" for p in data["providers"])
    assert any(p["id"] == "google_fact_check" for p in data["providers"])


def test_api_single_provider_detail():
    client = TestClient(app)
    resp = client.get("/api/v1/integrations/toi_national")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "toi_national"
    assert data["category"] == "National"
    assert data["requires_api_key"] is False


def test_api_connection_test_without_key():
    client = TestClient(app)
    # Test with unconfigured Currents key by patching settings.CURRENTS_API_KEY to None
    with patch("backend.config.settings.CURRENTS_API_KEY", None):
        from backend.api.dependencies import get_integration_manager

        get_integration_manager.cache_clear()
        resp = client.post("/api/v1/integrations/currents/test")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is False
        assert data["status"] == "not_configured"


def test_api_connection_test_rss_feed():
    client = TestClient(app)
    # Mock RSS fetch to avoid external HTTP call during test
    with patch("src.ingestion.rss.RssIngestionService.fetch_feed_result") as mock_fetch:
        from src.ingestion.models import ProviderFetchResult

        mock_fetch.return_value = ProviderFetchResult(
            source_id="rss_test",
            source_name="The Times of India (National)",
            source_type="rss",
            status=STATUS_SUCCESS,
            articles=[],
            items_count=10,
            http_status=200,
        )
        resp = client.post("/api/v1/integrations/toi_national/test")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["success"] is True
        assert data["status"] == "connected"


def test_api_quota_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/integrations/newsdata_io/quota")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["provider_id"] == "newsdata_io"
    assert data["quota_supported"] is True
    assert data["unit"] == "requests"
    assert data["source"] == "newslens_request_budget"
    assert data["used"] is not None
    assert data["limit"] is not None
    assert data["rolling_15m_used"] is not None


def test_api_secrets_never_exposed():
    """Security audit test: verifies that configured or raw API keys never appear in REST responses."""
    client = TestClient(app)
    with (
        patch("backend.config.settings.NEWSDATA_API_KEY", "super_secret_key_12345"),
        patch("backend.config.settings.CURRENTS_API_KEY", "curr_secret_key_67890"),
        patch("backend.config.settings.GUARDIAN_API_KEY", "guard_secret_key_99999"),
    ):
        resp = client.get("/api/v1/integrations")
        assert resp.status_code == 200
        text = resp.text
        assert "super_secret_key_12345" not in text
        assert "curr_secret_key_67890" not in text
        assert "guard_secret_key_99999" not in text

        # Test single provider
        r2 = client.get("/api/v1/integrations/guardian_open_platform")
        assert r2.status_code == 200
        assert "guard_secret_key_99999" not in r2.text


def test_api_admin_auth_in_production():
    """Security audit test: verifies that /test and /refresh require authentication in production."""
    client = TestClient(app)

    # 1. In production without admin key configured on server -> 503 Service Unavailable
    with (
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", None),
    ):
        res = client.post("/api/v1/integrations/currents/test")
        assert res.status_code == 503

    # 2. In production with admin key configured, but client sends no header -> 401 Unauthorized
    with (
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999"),
    ):
        res = client.post("/api/v1/integrations/currents/test")
        assert res.status_code == 401

        # Client sends wrong key -> 401 Unauthorized
        res_wrong = client.post(
            "/api/v1/integrations/currents/test",
            headers={"X-Admin-Key": "wrong_key"},
        )
        assert res_wrong.status_code == 401

        # Client sends correct key -> 200 Authorized
        res_correct = client.post(
            "/api/v1/integrations/currents/test",
            headers={"X-Admin-Key": "prod_admin_secret_999"},
        )
        assert res_correct.status_code == 200

    # 3. In development mode without explicit auth requirement -> 200 allowed
    with (
        patch("backend.config.settings.APP_ENV", "development"),
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_IN_DEV", False),
    ):
        res_dev = client.post("/api/v1/integrations/currents/test")
        assert res_dev.status_code == 200
