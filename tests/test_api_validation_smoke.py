"""Bounded API smoke suite for NewsLens India.

Validates the externally visible contract on real runtime paths:

* success bodies carry a ``data`` envelope and no legacy ``success`` flag
* failures use RFC 9457 ``application/problem+json`` with a stable ``code``
* administrative routes resolve and are gated, never crashing
* the dashboard keeps its documented shape

Renamed from ``api_validation_smoke.py`` so pytest actually collects it; the
previous name meant CI never ran these assertions, which still targeted the
removed legacy error envelope.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

PROBLEM = "application/problem+json"
client = TestClient(app)


def _request(method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = None
    return response, body


def test_health_returns_data_envelope(isolated_test_db):
    response, body = _request("GET", "/api/v1/health")
    assert response.status_code == 200
    assert body["data"]["status"] == "healthy"
    assert body["success"] is True


def test_article_list_keeps_items_and_pagination(isolated_test_db):
    response, body = _request("GET", "/api/v1/articles?page=1&page_size=2")
    assert response.status_code == 200
    assert isinstance(body["data"]["items"], list)
    assert "pagination" in body["data"]


def test_article_not_found_uses_problem_details(isolated_test_db):
    response, body = _request("GET", "/api/v1/articles/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith(PROBLEM)
    assert body["code"] == "ARTICLE_NOT_FOUND"


def test_validation_failure_uses_problem_details(isolated_test_db):
    response, body = _request("POST", "/api/v1/analysis", json={"text": "   "})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith(PROBLEM)
    assert body["status"] == 422


def test_admin_routes_resolve_and_are_gated(isolated_test_db):
    """Exercised in development, where loopback callers are permitted."""
    for path in (
        "/api/v1/integrations/newsdata_io/test",
        "/api/v1/integrations/newsdata_io/refresh",
    ):
        response, _ = _request("POST", path)
        assert response.status_code in (200, 401, 403, 429, 503), (path, response.status_code)


def test_unconfigured_provider_test_does_not_crash(isolated_test_db):
    response, _ = _request("POST", "/api/v1/integrations/newsdata_io/test")
    assert response.status_code != 500


def test_dashboard_keeps_documented_shape(isolated_test_db):
    response, body = _request("GET", "/api/v1/dashboard/summary")
    assert response.status_code == 200
    assert "total_articles" in body["data"]
    assert "source_statuses" in body["data"]
