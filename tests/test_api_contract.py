"""Contract, security, and pagination quality gates for the NewsLens API boundary."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import (
    app,
    reset_rate_limits,
    validate_security_configuration,
)
from scripts.export_openapi import ARTIFACT, build_spec, serialize
from src.ingestion.models import RefreshResult

PROBLEM_MEDIA_TYPE = "application/problem+json"
REMOTE_CLIENT = ("203.0.113.9", 51234)


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


def client(host: tuple[str, int] | None = None) -> TestClient:
    return TestClient(app) if host is None else TestClient(app, client=host)


def _stub_refresh(*_args, **_kwargs) -> RefreshResult:
    """Deterministic, offline stand-in for a live RSS refresh."""
    return RefreshResult(
        total_fetched=0,
        new_stored=0,
        duration_ms=0.0,
        provider_results={},
        all_succeeded=True,
        all_failed=False,
    )


# --------------------------------------------------------------------------- contract


def test_openapi_artifact_is_current():
    assert ARTIFACT.exists(), "docs/openapi.json is missing; run scripts/export_openapi.py"
    assert ARTIFACT.read_text(encoding="utf-8") == serialize(build_spec())


def test_openapi_operations_are_documented():
    spec = build_spec()
    operation_ids: list[str] = []

    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            assert operation_id, f"{method.upper()} {path} has no operationId"
            operation_ids.append(operation_id)
            assert operation.get("summary"), f"{method.upper()} {path} has no summary"
            assert operation.get("tags"), f"{method.upper()} {path} has no tags"
            responses = operation.get("responses", {})
            assert responses, f"{method.upper()} {path} has no responses"
            assert "default" in responses, "every operation must document its failures"

    assert len(operation_ids) == len(set(operation_ids)), "operationIds must be unique"
    assert "ProblemDetails" in spec["components"]["schemas"]


# --------------------------------------------------------------------------- problems


def assert_problem(response, *, code: str, status: int) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body = response.json()
    assert body["type"] and body["type"].startswith("urn:newslens:problem:")
    assert body["title"]
    assert body["status"] == status
    assert body["code"] == code
    assert body["request_id"], "problem bodies must carry a correlation id"
    return body


def test_article_not_found_uses_problem_details(isolated_test_db):
    response = client().get("/api/v1/articles/does-not-exist")
    body = assert_problem(response, code="ARTICLE_NOT_FOUND", status=404)
    assert body["instance"] == "/api/v1/articles/does-not-exist"


def test_validation_error_uses_problem_details(isolated_test_db):
    response = client().post("/api/v1/analysis", json={"text": "   "})
    body = assert_problem(response, code="VALIDATION_ERROR", status=422)
    assert body["errors"], "validation problems must include field-level errors"
    assert body["errors"][0]["field"].startswith("body")
    assert "input" not in str(body), "submitted values must not be echoed back"


def test_query_validation_error_uses_problem_details(isolated_test_db):
    assert_problem(client().get("/api/v1/articles?page=0"), code="VALIDATION_ERROR", status=422)


def test_unhandled_exception_returns_generic_problem(isolated_test_db):
    crashing = TestClient(app, raise_server_exceptions=False)
    with patch(
        "src.services.news_service.NewsLensService.get_source_statuses",
        side_effect=RuntimeError("database exploded at /secret/path"),
    ):
        response = crashing.get("/api/v1/ingestion/status")

    body = assert_problem(response, code="INTERNAL_ERROR", status=500)
    assert "exploded" not in str(body)
    assert "/secret/path" not in str(body)


def test_request_id_is_echoed_and_generated(isolated_test_db):
    echo = client().get("/api/v1/health", headers={"X-Request-ID": "abc12345-valid"})
    assert echo.headers["X-Request-ID"] == "abc12345-valid"

    generated = client().get("/api/v1/health", headers={"X-Request-ID": "bad id!!"})
    generated_id = generated.headers["X-Request-ID"]
    assert generated_id != "bad id!!"
    assert len(generated_id) == 32


# ---------------------------------------------------------------------------- security


def test_enforcement_without_admin_key_fails_closed_at_startup():
    with pytest.raises(RuntimeError, match="ADMIN_API_KEY"):
        validate_security_configuration(
            Settings(
                APP_ENV="development",
                REQUIRE_ADMIN_AUTH_FOR_INGESTION=True,
                ADMIN_API_KEY=None,
            )
        )


def test_invalid_environment_is_rejected():
    with pytest.raises(RuntimeError, match="APP_ENV"):
        validate_security_configuration(Settings(APP_ENV="prod", ADMIN_API_KEY="x" * 24))


def test_short_admin_key_is_rejected():
    with pytest.raises(RuntimeError, match="at least"):
        validate_security_configuration(Settings(APP_ENV="production", ADMIN_API_KEY="short"))


def test_ingestion_is_ungated_by_default(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", False),
        patch("src.services.news_service.NewsLensService.refresh_rss_feeds", _stub_refresh),
    ):
        response = client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"})
        assert response.status_code == 200


def test_gated_ingestion_rejects_missing_or_blank_key(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999"),
    ):
        assert_problem(
            client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"}),
            code="UNAUTHORIZED",
            status=401,
        )
        assert_problem(
            client().post(
                "/api/v1/ingestion/refresh",
                json={"source_type": "rss"},
                headers={"X-Admin-Key": "   "},
            ),
            code="UNAUTHORIZED",
            status=401,
        )


def test_gated_ingestion_accepts_valid_key(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999"),
        patch("src.services.news_service.NewsLensService.refresh_rss_feeds", _stub_refresh),
    ):
        response = client().post(
            "/api/v1/ingestion/refresh",
            json={"source_type": "rss"},
            headers={"X-Admin-Key": "prod_admin_secret_999"},
        )
        assert response.status_code == 200


def test_gated_ingestion_missing_server_config_fails_closed(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "production"),
        patch("backend.config.settings.ADMIN_API_KEY", None),
    ):
        assert_problem(
            client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"}),
            code="SERVICE_UNAVAILABLE",
            status=503,
        )


def test_gated_ingestion_allows_loopback_in_development(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "development"),
        patch("backend.config.settings.ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV", True),
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_IN_DEV", False),
        patch("src.services.news_service.NewsLensService.refresh_rss_feeds", _stub_refresh),
    ):
        response = client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"})
        assert response.status_code == 200


def test_gated_ingestion_remote_client_cannot_bypass(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "development"),
        patch("backend.config.settings.ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV", True),
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_IN_DEV", False),
        patch("backend.config.settings.ADMIN_API_KEY", "dev_admin_secret_1234"),
    ):
        spoofed = client(REMOTE_CLIENT).post(
            "/api/v1/ingestion/refresh",
            json={"source_type": "rss"},
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert_problem(spoofed, code="UNAUTHORIZED", status=401)


def test_gated_ingestion_dev_bypass_can_be_disabled(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.APP_ENV", "development"),
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_IN_DEV", True),
        patch("backend.config.settings.ADMIN_API_KEY", "dev_admin_secret_1234"),
    ):
        assert_problem(
            client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"}),
            code="UNAUTHORIZED",
            status=401,
        )


def test_gated_ingestion_is_rate_limited(isolated_test_db):
    with (
        patch("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True),
        patch("backend.config.settings.ADMIN_RATE_LIMIT_PER_MINUTE", 1),
        patch("backend.config.settings.APP_ENV", "development"),
        patch("src.services.news_service.NewsLensService.refresh_rss_feeds", _stub_refresh),
    ):
        first = client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"})
        assert first.status_code == 200
        limited = client().post("/api/v1/ingestion/refresh", json={"source_type": "rss"})
        assert_problem(limited, code="RATE_LIMITED", status=429)
        assert "Retry-After" in limited.headers


# -------------------------------------------------------------------------- pagination


def test_pagination_pages_do_not_overlap(isolated_test_db):
    c = client()
    first = c.get("/api/v1/articles?page=1&page_size=10").json()["data"]
    second = c.get("/api/v1/articles?page=2&page_size=10").json()["data"]

    first_ids = [a["id"] for a in first["items"]]
    second_ids = [a["id"] for a in second["items"]]
    assert len(first_ids) == 10 and len(second_ids) == 10
    assert set(first_ids).isdisjoint(second_ids), "identical timestamps must not break paging"
    assert first["pagination"]["total_items"] == second["pagination"]["total_items"]


def test_pagination_rejects_out_of_range_values(isolated_test_db):
    c = client()
    for query in ("page=0", "page_size=0", "page_size=101"):
        assert_problem(c.get(f"/api/v1/articles?{query}"), code="VALIDATION_ERROR", status=422)


def test_pagination_deep_page_returns_empty_items(isolated_test_db):
    data = client().get("/api/v1/articles?page=9999&page_size=20").json()["data"]
    assert data["items"] == []
    assert data["pagination"]["total_pages"] >= 1


def test_dashboard_top_stories_capped_at_ten_unique(isolated_test_db):
    data = client().get("/api/v1/dashboard/summary").json()["data"]
    recent = data["recent_articles"]
    assert len(recent) <= 10
    assert data["top_stories_limit"] == 10
    assert data["top_stories_count"] == len(recent)
    assert len({a["id"] for a in recent}) == len(recent)


# ------------------------------------------------------------------------- idempotency


def test_manual_submission_is_idempotent_for_identical_payload(isolated_test_db):
    c = client()
    payload = {
        "title": "Retry safety check: municipal water tariff notice",
        "publisher": "Civic Wire",
        "url": "https://example.com/retry-safety-water-tariff",
        "summary": "Submitted twice to verify no duplicate rows are created.",
    }

    first = c.post("/api/v1/articles", json=payload)
    assert first.status_code == 201
    first_id = first.json()["data"]["id"]

    total_after_first = c.get("/api/v1/articles?page=1&page_size=1").json()["data"][
        "pagination"
    ]["total_items"]

    second = c.post("/api/v1/articles", json=payload)
    assert second.status_code == 201
    assert second.json()["data"]["id"] == first_id

    total_after_second = c.get("/api/v1/articles?page=1&page_size=1").json()["data"][
        "pagination"
    ]["total_items"]
    assert total_after_second == total_after_first
