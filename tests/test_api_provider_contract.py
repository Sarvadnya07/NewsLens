"""Provider contract gates: normalized shapes, stable 404s, quotas, authorization.

Provider upstreams are always mocked here. A passing run proves the *contract*,
never live reachability of NewsData, Currents, Guardian, GDELT, or RSS.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app, reset_rate_limits
from src.ingestion.models import STATUS_SUCCESS, ProviderFetchResult

PROBLEM_MEDIA_TYPE = "application/problem+json"
REMOTE_CLIENT = ("203.0.113.9", 51234)

STATUS_STATES = {
    "operational",
    "degraded",
    "configured_not_tested",
    "not_configured",
    "disabled",
    "rate_limited",
    "provider_error",
    "backlog",
    "retired",
}


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


def client(host: tuple[str, int] | None = None) -> TestClient:
    return TestClient(app) if host is None else TestClient(app, client=host)


def _stub_rss_success(*_args, **_kwargs) -> ProviderFetchResult:
    """Offline stand-in for a successful RSS feed probe."""
    return ProviderFetchResult(
        source_id="rss_test",
        source_name="The Times of India (National)",
        source_type="rss",
        status=STATUS_SUCCESS,
        articles=[],
        items_count=3,
        http_status=200,
    )


def assert_problem(response, *, code: str, status: int) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["type"].startswith("urn:newslens:problem:")
    assert body["title"]
    assert body["status"] == status
    assert body["code"] == code
    assert body["request_id"]
    return body


# ------------------------------------------------------------------ stable failures


def test_unknown_provider_returns_stable_not_found(isolated_test_db):
    c = client()
    for path in (
        "/api/v1/integrations/does_not_exist/test",
        "/api/v1/integrations/does_not_exist/refresh",
    ):
        body = assert_problem(c.post(path), code="PROVIDER_NOT_FOUND", status=404)
        assert body["instance"] == path


def test_unknown_provider_quota_returns_stable_not_found(isolated_test_db):
    body = assert_problem(
        client().get("/api/v1/integrations/does_not_exist/quota"),
        code="PROVIDER_NOT_FOUND",
        status=404,
    )
    assert body["instance"] == "/api/v1/integrations/does_not_exist/quota"


# --------------------------------------------------------------- connection contract


def test_connection_test_has_stable_shape(isolated_test_db):
    with patch("src.ingestion.rss.RssIngestionService.fetch_feed_result", _stub_rss_success):
        response = client().post("/api/v1/integrations/toi_national/test")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["provider_id"] == "toi_national"
    assert data["status"] == "connected"
    assert data["connected"] is True
    assert data["success"] is True
    assert data["configured"] is True
    assert data["implemented"] is True
    assert data["checked_at"]
    assert data["error"] is None
    assert data["http_status"] == 200
    assert data["request_id"]


def test_connection_test_reports_missing_credentials(isolated_test_db):
    from backend.api.dependencies import get_integration_manager

    with (
        patch("backend.config.settings.CURRENTS_API_KEY", None),
        patch("backend.config.settings.CURRENTS_ENABLED", False),
    ):
        get_integration_manager.cache_clear()
        try:
            response = client().post("/api/v1/integrations/currents/test")
        finally:
            get_integration_manager.cache_clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "not_configured"
    assert data["connected"] is False
    assert data["success"] is False
    assert data["configured"] is False
    assert data["implemented"] is True
    assert data["error"], "an unsuccessful test must explain itself"


# ---------------------------------------------------------------------------- quota


def test_quota_reports_a_supported_request_budget(isolated_test_db):
    data = client().get("/api/v1/integrations/newsdata_io/quota").json()["data"]
    assert data["quota_supported"] is True
    assert data["unit"] == "requests"
    assert data["source"] == "newslens_request_budget"
    assert data["limit"] is not None
    assert data["used"] is not None
    assert data["remaining"] is not None
    assert data["rolling_15m_used"] is not None


def test_quota_is_explicitly_unsupported_without_a_budget(isolated_test_db):
    data = client().get("/api/v1/integrations/toi_national/quota").json()["data"]
    assert data["provider_id"] == "toi_national"
    assert data["quota_supported"] is False
    assert data["used"] is None
    assert data["limit"] is None
    assert data["remaining"] is None


# --------------------------------------------------------------------- authorization


def test_provider_diagnostics_require_admin_key_in_production(isolated_test_db):
    with (
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999"),
    ):
        for path in (
            "/api/v1/integrations/toi_national/test",
            "/api/v1/integrations/toi_national/refresh",
        ):
            # A remote client cannot bypass; neither can a spoofed forwarding header.
            assert_problem(
                client(REMOTE_CLIENT).post(path, headers={"X-Forwarded-For": "127.0.0.1"}),
                code="UNAUTHORIZED",
                status=401,
            )


def test_provider_diagnostics_accept_valid_admin_key(isolated_test_db):
    with (
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999"),
        patch("src.ingestion.rss.RssIngestionService.fetch_feed_result", _stub_rss_success),
    ):
        response = client(REMOTE_CLIENT).post(
            "/api/v1/integrations/toi_national/test",
            headers={"X-Admin-Key": "prod_admin_secret_999"},
        )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "connected"


# --------------------------------------------------------------- truthful statuses


def test_provider_status_labels_use_the_canonical_vocabulary(isolated_test_db):
    providers = client().get("/api/v1/integrations/status").json()["data"]
    assert providers, "the registry must expose providers"

    for provider in providers:
        assert provider["status_label"] in STATUS_STATES, provider["id"]

    for provider in providers:
        if provider["status_label"] in {"backlog", "retired"}:
            assert provider["is_active"] is False, (
                f"{provider['id']} is a {provider['status_label']} provider and "
                "must not be reported as an active implementation"
            )


def test_operational_status_requires_recorded_evidence(isolated_test_db):
    providers = client().get("/api/v1/integrations/status").json()["data"]
    for provider in providers:
        if provider["status_label"] == "operational":
            assert provider["last_attempt_at"] or provider["last_refresh_at"], (
                f"{provider['id']} claims operational without any recorded attempt"
            )
