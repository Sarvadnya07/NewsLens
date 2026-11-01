"""Comprehensive regression and verification test suite for Stage 2-3 Remediation.

Covers:
1. Test isolation and real data safety.
2. Additive, idempotent schema migrations on disposable copy.
3. Origin column persistence and manual record preservation.
4. Deccan Herald retirement (is_active=0).
5. Canonical GDELT provider identity (no query-string pollution).
6. Telemetry persistence (last_successful_refresh_at preserved across failures).
7. Refresh-all partial success semantics.
8. Database SQL aggregations vs manual counting.
9. Coverage clustering TTL caching.
10. FastAPI TestClient operational endpoints.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from src.ingestion.models import (
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ProviderFetchResult,
    RefreshResult,
)
from src.ingestion.registry import (
    CANONICAL_GDELT_NAME,
    CANONICAL_NEWSDATA_NAME,
    get_active_providers,
    get_active_rss_feeds,
    get_gdelt_provider,
    get_newsdata_provider,
    get_retired_providers,
)
from src.models import NormalizedArticle
from src.services.news_service import NewsLensService
from src.storage.database import DatabaseManager
from src.storage.migrations import MIGRATION_REGISTRY, get_applied_migrations, run_migrations

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_DB_PATH = PROJECT_ROOT / "data" / "newslens.db"
BACKUP_DB_PATH = PROJECT_ROOT / "data" / "newslens.db.backup"
EXPECTED_BACKUP_SHA256 = "ace1c0f756af5a17f7d1b830202b05fca2cee5a8ef56bd2b1972d9f6a0bb8b0f"


def test_test_isolation_and_data_safety():
    """Verify test environment runs in an isolated temp database and never touches real data."""
    active_db = os.environ.get("NEWSLENS_DB_PATH")
    assert active_db is not None, "NEWSLENS_DB_PATH must be set in tests"
    resolved_active = Path(active_db).resolve()

    # Must NOT point to real DB or backup DB
    assert resolved_active != REAL_DB_PATH.resolve(), (
        "CRITICAL: Tests running against data/newslens.db!"
    )
    assert resolved_active != BACKUP_DB_PATH.resolve(), (
        "CRITICAL: Tests running against data/newslens.db.backup!"
    )

    # Must be in system temp directory
    temp_dir = tempfile.gettempdir().lower()
    assert temp_dir in str(resolved_active).lower() or "pytest" in str(resolved_active).lower(), (
        f"Test DB {resolved_active} is not in a temporary directory"
    )

    # Verify real backup SHA-256 remains completely unaltered
    assert BACKUP_DB_PATH.exists(), "data/newslens.db.backup must exist"
    actual_hash = hashlib.sha256(BACKUP_DB_PATH.read_bytes()).hexdigest()
    assert actual_hash == EXPECTED_BACKUP_SHA256, (
        f"Backup hash changed! Expected {EXPECTED_BACKUP_SHA256}, got {actual_hash}"
    )


def test_migration_idempotency_and_preservation_on_disposable_copy():
    """Verify migration 001 preserves all 823 articles and 4 manual records on disposable backup."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_copy = tf.name

    try:
        shutil.copyfile(str(BACKUP_DB_PATH), temp_copy)
        conn = sqlite3.connect(temp_copy)

        # Baseline inspection before migration
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM articles")
        initial_articles = c.fetchone()[0]
        assert initial_articles == 823, f"Expected 823 initial articles, found {initial_articles}"

        c.execute("SELECT COUNT(*) FROM articles WHERE source_type = 'manual'")
        initial_manual = c.fetchone()[0]
        assert initial_manual == 4, f"Expected 4 manual articles, found {initial_manual}"

        # Run first migration
        applied_first = run_migrations(conn)
        conn.commit()
        assert 1 in applied_first, "Migration 1 was not applied"

        # Verify columns added
        c.execute("PRAGMA table_info(articles)")
        art_cols = {row[1] for row in c.fetchall()}
        assert "origin" in art_cols, "'origin' column missing in articles"

        c.execute("PRAGMA table_info(source_status)")
        status_cols = {row[1] for row in c.fetchall()}
        expected_telemetry = {
            "last_attempt_at",
            "last_attempt_status",
            "last_successful_refresh_at",
            "last_http_status",
            "last_latency_ms",
            "new_items_inserted",
            "is_active",
        }
        assert expected_telemetry.issubset(status_cols), (
            f"Missing telemetry columns: {expected_telemetry - status_cols}"
        )

        # Verify article counts preserved
        c.execute("SELECT COUNT(*) FROM articles")
        post_articles = c.fetchone()[0]
        assert post_articles == 823, "Article count changed during migration!"

        # Verify manual articles preserved with origin='manual'
        c.execute("SELECT COUNT(*) FROM articles WHERE origin = 'manual'")
        post_manual = c.fetchone()[0]
        assert post_manual == 4, (
            f"Expected 4 manual records with origin='manual', found {post_manual}"
        )

        # Verify Deccan Herald retired with is_active=0
        c.execute("SELECT is_active FROM source_status WHERE source_name LIKE '%Deccan%'")
        deccan_row = c.fetchone()
        assert deccan_row is not None, "Deccan Herald missing from source_status"
        assert deccan_row[0] == 0, f"Deccan Herald is_active expected 0, got {deccan_row[0]}"

        # Run second migration to verify idempotency
        applied_second = run_migrations(conn)
        conn.commit()
        assert applied_second == [], (
            "Second migration run applied unexpected migrations (not idempotent)"
        )

        conn.close()
    finally:
        if os.path.exists(temp_copy):
            os.remove(temp_copy)


def test_origin_persistence_and_retrieval(tmp_path: Path):
    """Verify origin column persistence across upserts and retrieval."""
    test_db = str(tmp_path / "origin_test.db")
    db = DatabaseManager(db_path=test_db)

    now = "2026-11-01T00:00:00+00:00"
    articles = [
        NormalizedArticle(
            id="test_rss_1",
            title="RSS Test",
            url="https://example.com/rss1",
            publisher="Test Publisher",
            published_at=now,
            ingested_at=now,
            source_type="rss",
            origin="rss",
        ),
        NormalizedArticle(
            id="test_gdelt_1",
            title="GDELT Test",
            url="https://example.com/gdelt1",
            publisher="GDELT Publisher",
            published_at=now,
            ingested_at=now,
            source_type="gdelt",
            origin="gdelt",
        ),
        NormalizedArticle(
            id="manual_test_1",
            title="Manual Test",
            url="manual://test_1",
            publisher="Manual User Submission",
            published_at=now,
            ingested_at=now,
            source_type="manual",
            origin="manual",
        ),
    ]

    inserted = db.upsert_articles(articles)
    assert inserted == 3

    fetched = db.get_articles(limit=10)
    origin_map = {a.id: a.origin for a in fetched}
    assert origin_map["test_rss_1"] == "rss"
    assert origin_map["test_gdelt_1"] == "gdelt"
    assert origin_map["manual_test_1"] == "manual"


def test_gdelt_canonical_identity_and_no_query_pollution(tmp_path: Path):
    """Verify GDELT uses single canonical provider identity and does not create query-specific rows."""
    test_db = str(tmp_path / "gdelt_canon.db")
    service = NewsLensService(db_path=test_db)

    # Mock GDELT fetch returning 2 articles
    now = "2026-11-01T00:00:00+00:00"
    mock_articles = [
        NormalizedArticle(
            id="gdelt_art_1",
            title="India Tech Summit",
            url="https://tech.example.com/summit",
            publisher="Tech India",
            published_at=now,
            ingested_at=now,
            source_type="gdelt",
            origin="gdelt",
        )
    ]
    with patch.object(
        service.gdelt,
        "fetch_articles",
        return_value=ProviderFetchResult(
            source_id="gdelt_doc_api",
            source_name=CANONICAL_GDELT_NAME,
            source_type="gdelt",
            status=STATUS_SUCCESS,
            articles=mock_articles,
            items_count=1,
            duration_ms=150.0,
            http_status=200,
        ),
    ):
        service.search_gdelt("AI India")
        service.search_gdelt("Budget 2026")

    # Inspect source_status table
    statuses = service.db.get_all_source_status()
    gdelt_rows = [s for s in statuses if s["source_type"] == "gdelt"]

    # There must be EXACTLY ONE GDELT row: CANONICAL_GDELT_NAME
    assert len(gdelt_rows) == 1, f"Expected 1 canonical GDELT row, found {len(gdelt_rows)}"
    assert gdelt_rows[0]["source_name"] == CANONICAL_GDELT_NAME
    assert "AI India" not in gdelt_rows[0]["source_name"]
    assert "Budget 2026" not in gdelt_rows[0]["source_name"]


def test_telemetry_preserves_last_success_across_failures(tmp_path: Path):
    """Verify last_successful_refresh_at is not wiped or overwritten when subsequent attempt fails."""
    test_db = str(tmp_path / "telemetry_test.db")
    db = DatabaseManager(db_path=test_db)

    source = "The Hindu (National)"

    # Step 1: Initial successful sync
    db.record_source_status(
        source_name=source,
        source_type="rss",
        status=STATUS_SUCCESS,
        items_fetched=20,
        http_status=200,
        latency_ms=110.0,
    )
    st1 = db.get_source_status(source)
    assert st1 is not None
    assert st1["status"] == STATUS_SUCCESS
    initial_success_ts = st1["last_successful_refresh_at"]
    assert initial_success_ts is not None

    time.sleep(0.01)

    # Step 2: Subsequent attempt encounters HTTP 503 / provider_unavailable
    db.record_source_status(
        source_name=source,
        source_type="rss",
        status=STATUS_PROVIDER_UNAVAILABLE,
        items_fetched=0,
        error_message="HTTP 503 Service Unavailable",
        http_status=503,
        latency_ms=450.0,
    )
    st2 = db.get_source_status(source)
    assert st2 is not None
    assert st2["status"] == STATUS_PROVIDER_UNAVAILABLE
    assert st2["last_attempt_status"] == STATUS_PROVIDER_UNAVAILABLE
    assert st2["last_http_status"] == 503

    # CRITICAL: last_successful_refresh_at must still be the initial timestamp!
    assert st2["last_successful_refresh_at"] == initial_success_ts, (
        "last_successful_refresh_at was overwritten by failed attempt!"
    )


def test_refresh_all_partial_success(tmp_path: Path):
    """Verify refresh_all executes both RSS and GDELT and reports honest partial success."""
    test_db = str(tmp_path / "refresh_all_test.db")
    service = NewsLensService(db_path=test_db)

    # Mock RSS success
    mock_rss_res = RefreshResult(
        total_fetched=10,
        new_stored=10,
        duration_ms=100.0,
        provider_results={
            "The Hindu (National)": ProviderFetchResult(
                source_id="the_hindu",
                source_name="The Hindu (National)",
                source_type="rss",
                status=STATUS_SUCCESS,
                items_count=10,
            )
        },
        all_succeeded=True,
        all_failed=False,
    )

    # Mock GDELT failure (timeout)
    mock_gdelt_res = ProviderFetchResult(
        source_id="gdelt_doc_api",
        source_name=CANONICAL_GDELT_NAME,
        source_type="gdelt",
        status=STATUS_TIMEOUT,
        items_count=0,
        duration_ms=5000.0,
        error_message="Connection timed out",
    )

    with (
        patch.object(service, "refresh_rss_feeds", return_value=mock_rss_res),
        patch.object(service, "refresh_gdelt", return_value=mock_gdelt_res),
    ):
        result = service.refresh_all(gdelt_query="India")

    assert result.total_fetched == 10
    assert result.all_succeeded is False
    assert result.all_failed is False
    assert CANONICAL_GDELT_NAME in result.provider_results
    assert "The Hindu (National)" in result.provider_results
    assert result.provider_results[CANONICAL_GDELT_NAME].status == STATUS_TIMEOUT
    assert result.provider_results["The Hindu (National)"].status == STATUS_SUCCESS


def test_database_sql_aggregations(tmp_path: Path):
    """Verify database-level SQL aggregations match expected counts without in-memory looping."""
    test_db = str(tmp_path / "aggregations.db")
    db = DatabaseManager(db_path=test_db)

    now = "2026-11-01T00:00:00+00:00"
    articles = [
        NormalizedArticle(
            id=f"art_{i}",
            title=f"Article {i}",
            url=f"https://example.com/{i}",
            publisher="NDTV" if i < 7 else "The Hindu",
            published_at=now,
            ingested_at=now,
            source_type="rss" if i < 8 else "gdelt",
            origin="rss" if i < 8 else "gdelt",
        )
        for i in range(10)
    ]
    db.upsert_articles(articles)

    sources_dist = db.get_sources_distribution()
    assert sources_dist["rss"] == 8
    assert sources_dist["gdelt"] == 2

    pub_dist = db.get_publishers_distribution(limit=5)
    assert pub_dist["NDTV"] == 7
    assert pub_dist["The Hindu"] == 3


def test_coverage_clustering_ttl_cache(tmp_path: Path):
    """Verify coverage clustering is cached and not recomputed on every call within TTL."""
    test_db = str(tmp_path / "cache_clusters.db")
    service = NewsLensService(db_path=test_db)

    with patch.object(
        service.deduplicator,
        "find_related_and_duplicates",
        return_value=[{"cluster_id": "c1", "total_coverage_count": 2}],
    ) as mock_find:
        # First call: computes and caches
        res1 = service.get_cached_coverage_clusters()
        assert len(res1) == 1
        assert mock_find.call_count == 1

        # Second call immediately after: returns cached object
        res2 = service.get_cached_coverage_clusters()
        assert len(res2) == 1
        assert mock_find.call_count == 1, "Clustering was recomputed despite active cache TTL!"

        # Force refresh: recomputes
        res3 = service.get_cached_coverage_clusters(force_refresh=True)
        assert len(res3) == 1
        assert mock_find.call_count == 2


def test_fastapi_endpoints_integration():
    """Verify all FastAPI routes respond cleanly with HTTP 200 and valid schemas."""
    client = TestClient(app)

    # 1. Health endpoint
    r_health = client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["data"]["status"] == "healthy"

    # 2. Dashboard summary endpoint
    r_dash = client.get("/api/v1/dashboard/summary")
    assert r_dash.status_code == 200
    data = r_dash.json()["data"]
    assert "total_articles" in data
    assert "sources_distribution" in data
    assert "publishers_distribution" in data
    assert data["total_configured_sources"] >= 7

    # 3. Ingestion status endpoint
    r_ing = client.get("/api/v1/ingestion/status")
    assert r_ing.status_code == 200
    assert "source_statuses" in r_ing.json()["data"]

    # 4. Ingestion refresh with source_type="all" (mocked)
    with patch("src.services.news_service.NewsLensService.refresh_all") as mock_ref_all:
        mock_ref_all.return_value = RefreshResult(
            total_fetched=5,
            new_stored=2,
            duration_ms=120.0,
            provider_results={
                "GDELT 2.0 Doc API": ProviderFetchResult(
                    source_id="gdelt_doc_api",
                    source_name="GDELT 2.0 Doc API",
                    source_type="gdelt",
                    status="success",
                    items_count=5,
                )
            },
            all_succeeded=True,
            all_failed=False,
        )
        r_ref = client.post("/api/v1/ingestion/refresh", json={"source_type": "all"})
        assert r_ref.status_code == 200
        assert r_ref.json()["data"]["total_fetched"] == 5
        assert r_ref.json()["data"]["new_stored"] == 2

    # 5. Articles list endpoint
    r_art = client.get("/api/v1/articles?page=1&page_size=5")
    assert r_art.status_code == 200
    assert len(r_art.json()["data"]["items"]) > 0

    # 6. Text analysis screening endpoint
    r_analysis = client.post(
        "/api/v1/analysis",
        json={"text": "Government announces major railway modernization program across India."},
    )
    assert r_analysis.status_code == 200
    assert "screening" in r_analysis.json()["data"]
    assert "label" in r_analysis.json()["data"]["screening"]

    # 7. Fact check evidence search endpoint
    r_ev = client.post(
        "/api/v1/evidence/search",
        json={"query": "demonetization currency exchange", "top_k": 2},
    )
    assert r_ev.status_code == 200
    assert "matches" in r_ev.json()["data"]


def test_authoritative_provider_registry_integrity():
    """Verify single canonical provider registry centralizes all active, on-demand, and retired sources."""
    active = get_active_providers()
    active_rss = get_active_rss_feeds()
    gdelt = get_gdelt_provider()
    retired = get_retired_providers()

    assert len(active) == 8, (
        f"Expected 8 active providers (6 RSS + 1 GDELT + 1 NewsData), got {len(active)}"
    )
    assert len(active_rss) == 6, f"Expected 6 active RSS feeds, got {len(active_rss)}"
    assert gdelt.name == CANONICAL_GDELT_NAME
    assert gdelt.is_on_demand is True
    assert gdelt.is_active is True

    newsdata = get_newsdata_provider()
    assert newsdata.name == CANONICAL_NEWSDATA_NAME
    assert newsdata.id == "newsdata_io"
    assert newsdata.source_type == "newsdata"
    assert newsdata.is_active is True

    # Deccan Herald must be cataloged as retired
    assert any("Deccan" in p.name for p in retired)
    assert all(not p.is_active for p in retired)


def test_migration_atomic_rollback_on_failure(tmp_path: Path):
    """Verify that a failing migration rolls back cleanly to savepoint and leaves schema_migrations untouched."""
    test_db = str(tmp_path / "rollback_test.db")
    db = DatabaseManager(db_path=test_db)

    with db._connect() as conn:
        applied_before = get_applied_migrations(conn)
        assert 1 in applied_before

        # Define a failing dummy migration 999
        def _bad_migration(c: sqlite3.Connection):
            c.execute("CREATE TABLE dummy_rollback_test (id INTEGER PRIMARY KEY)")
            raise sqlite3.OperationalError("Simulated catastrophic disk / syntax failure")

        MIGRATION_REGISTRY.append((999, "999_faulty_migration", _bad_migration))

        try:
            with pytest.raises(sqlite3.OperationalError):
                run_migrations(conn)

            # Confirm migration 999 was NOT recorded as applied
            applied_after = get_applied_migrations(conn)
            assert 999 not in applied_after

            # Confirm dummy table was rolled back and does not exist
            c = conn.cursor()
            c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dummy_rollback_test'"
            )
            assert c.fetchone() is None, "Failed migration's changes were not rolled back!"
        finally:
            MIGRATION_REGISTRY.pop()


def test_clustering_cache_invalidation_on_ingestion(tmp_path: Path):
    """Verify that clustering cache invalidates when new articles are ingested or manually submitted."""
    test_db = str(tmp_path / "cache_inval.db")
    service = NewsLensService(db_path=test_db)

    # Initial clustering
    service.get_cached_coverage_clusters()
    assert service._clusters_cache is not None

    # Submit manual article -> must invalidate cache
    service.submit_manual_article(
        title="Breaking news update for cluster invalidation",
        summary="Testing cache invalidation logic on write operations.",
    )
    assert service._clusters_cache is None, (
        "Clustering cache was not invalidated after article submission!"
    )

    # Next call computes fresh clusters
    service.get_cached_coverage_clusters()
    assert service._clusters_cache is not None


def test_api_refresh_all_http_outcomes_and_provider_invocation():
    """Verify HTTP endpoint POST /api/v1/ingestion/refresh with source_type='all' invokes both RSS and GDELT."""
    client = TestClient(app)

    # Scenario 1: All Succeeded
    mock_rss_result = {
        "articles": [
            NormalizedArticle(
                id="rss_test_art",
                title="RSS Story",
                url="https://thehindu.com/art1",
                publisher="The Hindu",
                published_at="2026-11-01T00:00:00+00:00",
                ingested_at="2026-11-01T00:00:00+00:00",
                source_type="rss",
            )
        ],
        "stats": {
            "The Hindu (National)": {
                "status": "success",
                "count": 1,
                "duration_ms": 100.0,
                "http_status": 200,
            }
        },
        "provider_results": {
            "The Hindu (National)": ProviderFetchResult(
                source_id="the_hindu",
                source_name="The Hindu (National)",
                source_type="rss",
                status="success",
                items_count=1,
                http_status=200,
            )
        },
    }

    mock_gdelt_success = ProviderFetchResult(
        source_id="gdelt_doc_api",
        source_name=CANONICAL_GDELT_NAME,
        source_type="gdelt",
        status="success",
        items_count=1,
        http_status=200,
        articles=[
            NormalizedArticle(
                id="gdelt_test_art",
                title="GDELT Story",
                url="https://gdelt.org/art1",
                publisher="Global News",
                published_at="2026-11-01T00:00:00+00:00",
                ingested_at="2026-11-01T00:00:00+00:00",
                source_type="gdelt",
            )
        ],
    )

    with (
        patch(
            "src.ingestion.rss.RssIngestionService.fetch_all", return_value=mock_rss_result
        ) as mock_rss,
        patch(
            "src.ingestion.gdelt.GdeltClient.fetch_articles", return_value=mock_gdelt_success
        ) as mock_gdelt,
    ):
        res = client.post("/api/v1/ingestion/refresh", json={"source_type": "all"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["all_succeeded"] is True
        assert data["all_failed"] is False
        assert mock_rss.called
        assert mock_gdelt.called
        assert CANONICAL_GDELT_NAME in data["summary"]
        assert "The Hindu (National)" in data["summary"]

    # Scenario 2: Partial Success (RSS succeeds, GDELT times out)
    mock_gdelt_timeout = ProviderFetchResult(
        source_id="gdelt_doc_api",
        source_name=CANONICAL_GDELT_NAME,
        source_type="gdelt",
        status=STATUS_TIMEOUT,
        items_count=0,
        error_message="Connection timed out",
    )

    with (
        patch("src.ingestion.rss.RssIngestionService.fetch_all", return_value=mock_rss_result),
        patch("src.ingestion.gdelt.GdeltClient.fetch_articles", return_value=mock_gdelt_timeout),
    ):
        res_partial = client.post("/api/v1/ingestion/refresh", json={"source_type": "all"})
        assert res_partial.status_code == 200
        data_p = res_partial.json()["data"]
        assert data_p["all_succeeded"] is False
        assert data_p["all_failed"] is False  # Partial success!
        assert "timeout" in data_p["summary"][CANONICAL_GDELT_NAME].lower()
        assert "success" in data_p["summary"]["The Hindu (National)"].lower()

    # Scenario 3: All Failed (Both RSS and GDELT fail)
    mock_rss_failed = {
        "articles": [],
        "stats": {
            "The Hindu (National)": {
                "status": "provider_unavailable",
                "count": 0,
                "error": "HTTP 503",
            }
        },
        "provider_results": {
            "The Hindu (National)": ProviderFetchResult(
                source_id="the_hindu",
                source_name="The Hindu (National)",
                source_type="rss",
                status=STATUS_PROVIDER_UNAVAILABLE,
                items_count=0,
            )
        },
    }

    with (
        patch("src.ingestion.rss.RssIngestionService.fetch_all", return_value=mock_rss_failed),
        patch("src.ingestion.gdelt.GdeltClient.fetch_articles", return_value=mock_gdelt_timeout),
    ):
        res_fail = client.post("/api/v1/ingestion/refresh", json={"source_type": "all"})
        assert res_fail.status_code == 200
        data_f = res_fail.json()["data"]
        assert data_f["all_succeeded"] is False
        assert data_f["all_failed"] is True
