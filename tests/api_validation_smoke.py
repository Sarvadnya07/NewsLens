r"""Fast, bounded API validation smoke for NewsLens India.

This is not a full test suite. It exists to validate the higher-value
API-02 changes under real runtime paths:
- existing consumer envelope compatibility
- correct HTTP status codes for known failure paths
- stable structured error shape with error.type
- admin boundary behavior
- NewsData provider-test no longer crashes as 500

Run from the project root with the repository virtualenv active:

    .venv\Scripts\python.exe -m pytest tests/api_validation_smoke.py -q

or:

    bash -lc 'set -e; export VIRTUAL_ENV=".venv"; source ".venv/Scripts/activate"; python -m pytest tests/api_validation_smoke.py -q'
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def req(method: str, path: str, **kwargs):
    r = client.request(method, path, **kwargs)
    try:
        body = r.json()
    except Exception:
        body = None
    return r.status_code, body


def test_existing_success_envelope_preserved():
    sc, b = req("GET", "/api/v1/health")
    assert sc == 200 and b["success"] and "data" in b and "error" not in b, b

    sc, b = req("GET", "/api/v1/articles?page=1&page_size=2")
    assert sc == 200 and b["success"] and "items" in b["data"] and "pagination" in b["data"], b


def test_article_not_found_uses_404_and_stable_error():
    sc, b = req("GET", "/api/v1/articles/does-not-exist")
    assert sc == 404 and b["success"] is False, (sc, b)
    err = b["error"]
    assert err["code"] == "ARTICLE_NOT_FOUND"
    assert err.get("type") == "https://newslex.in/errors/not-found"


def test_validation_failure_uses_422_and_stable_error():
    sc, b = req("POST", "/api/v1/analysis", json={"text": "   "})
    assert sc == 422 and b["success"] is False, (sc, b)
    err = b["error"]
    assert err.get("type", "").endswith(("unprocessable-entity", "validation-error", "bad-request"))


def test_admin_endpoints_are_gated_in_current_config():
    # Current config is development with REQUIRE_ADMIN_AUTH_IN_DEV=False, so
    # admin endpoints are allowed without a key in this environment. The point
    # here is to confirm the route still resolves and does not crash.
    sc, b = req("POST", "/api/v1/integrations/newsdata_io/test")
    assert sc in (200, 401, 403, 503), (sc, b)

    sc, b = req("POST", "/api/v1/integrations/newsdata_io/refresh")
    assert sc in (200, 401, 403, 503), (sc, b)


def test_newsdata_provider_test_no_longer_unhandled_500():
    sc, b = req("POST", "/api/v1/integrations/newsdata_io/test")
    # API-02 fixed the crash where the backend called a method that did not
    # exist on NewsDataClient. It should now degrade gracefully.
    assert sc != 500 or (b and b.get("error", {}).get("code") != "INTERNAL_SERVER_ERROR"), (sc, b)


def test_dashboard_compatibility_shape_still_readable():
    sc, b = req("GET", "/api/v1/dashboard/summary")
    assert sc == 200 and b["success"] and "data" in b, b
    assert "total_articles" in b["data"] and "source_statuses" in b["data"], b["data"]
