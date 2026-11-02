"""Backend hardening regression gates.

Covers the BACKEND-02 fixes: foreign-key enforcement, atomic article+telemetry
writes, legacy-schema migration and index usage, bounded pagination, error
taxonomy completeness, readiness semantics, and refresh single-flight.
"""

from __future__ import annotations

import ast
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_news_service
from backend.api.errors import ERROR_TAXONOMY, problem_type_for
from backend.main import app, refresh_coordinator
from src.models import NormalizedArticle
from src.storage.database import DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _article(index: int) -> NormalizedArticle:
    now = datetime.now(timezone.utc).isoformat()
    return NormalizedArticle(
        id=f"hardening_{index:04d}",
        title=f"Hardening article {index}",
        url=f"https://example.com/hardening/{index}",
        publisher="Example Wire",
        published_at=now,
        ingested_at=now,
        source_type="rss",
        summary="Regression fixture",
        language="en",
        country="IN",
        query="",
        origin="rss",
    )


def _status_row(name: str = "Hardening Feed") -> dict:
    return {
        "source_name": name,
        "source_type": "rss",
        "status": "success",
        "items_fetched": 2,
        "http_status": 200,
        "latency_ms": 12.5,
        "is_active": 1,
    }


# ------------------------------------------------------------------ integrity


def test_foreign_keys_are_enforced(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "fk.db"))
    with pytest.raises(sqlite3.IntegrityError):
        db.record_discovery(article_id="does-not-exist", provider_id="rss_syndicate")


def test_articles_and_telemetry_commit_atomically(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "atomic.db"))
    with pytest.raises(TypeError):
        # Incomplete telemetry row: must abort the whole transaction.
        db.upsert_articles([_article(1)], status_rows=[{"source_name": "Incomplete"}])

    assert db.get_article_count() == 0
    assert db.get_source_status("Incomplete") is None


def test_status_rows_are_written_with_the_batch(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "batch.db"))
    inserted = db.upsert_articles([_article(1), _article(2)], status_rows=[_status_row()])

    assert inserted == 2
    status = db.get_source_status("Hardening Feed")
    assert status is not None
    assert status["status"] == "success"
    # Caller omitted new_items_inserted: the batch count is filled in.
    assert status["new_items_inserted"] == 2


def test_concurrent_writers_converge_without_duplicates(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "concurrent.db"))
    articles = [_article(i) for i in range(25)]
    errors: list[BaseException] = []
    barrier = threading.Barrier(3)

    def writer() -> None:
        try:
            barrier.wait(timeout=5)
            db.upsert_articles(list(articles))
        except BaseException as exc:  # noqa: BLE001 - surfaced through the assertion below
            errors.append(exc)

    threads = [threading.Thread(target=writer) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, f"concurrent writers raised: {errors}"
    assert db.get_article_count() == len(articles)


# ------------------------------------------------------------------ migrations


def test_legacy_schema_is_upgraded_and_indexed(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE articles (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
            publisher TEXT NOT NULL, published_at TEXT, ingested_at TEXT NOT NULL,
            source_type TEXT NOT NULL, summary TEXT, language TEXT, country TEXT,
            query TEXT, raw_metadata TEXT
        );
        CREATE TABLE source_status (
            source_name TEXT PRIMARY KEY, source_type TEXT NOT NULL,
            last_refresh_at TEXT NOT NULL, status TEXT NOT NULL,
            items_fetched INTEGER DEFAULT 0, error_message TEXT
        );
        """
    )
    conn.execute(
        "INSERT INTO articles (id, title, url, publisher, published_at, ingested_at, source_type) "
        "VALUES ('legacy1', 'Legacy', 'https://example.com/legacy', 'Wire', "
        "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 'rss')"
    )
    conn.commit()
    conn.close()

    db = DatabaseManager(db_path=str(path))
    assert db.get_article_by_id("legacy1").origin == "rss"

    conn = sqlite3.connect(path)
    versions = [
        row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    ]
    plan = [
        row[3]
        for row in conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM articles "
            "ORDER BY COALESCE(NULLIF(published_at, ''), ingested_at) DESC, id ASC LIMIT 20"
        )
    ]
    conn.close()

    assert versions == [1, 2, 3, 4]
    assert any("idx_articles_effective_date" in step for step in plan), plan


# ----------------------------------------------------------------- pagination


def test_out_of_range_page_is_a_validation_error_not_a_500(isolated_test_db):
    response = TestClient(app).get("/api/v1/articles?page=461168601842738790")

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------- taxonomy


def test_every_raised_error_code_is_documented():
    codes: set[str] = set()
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, "id", "") != "NewsLensAPIException":
                continue
            for keyword in node.keywords:
                if keyword.arg == "code" and isinstance(keyword.value, ast.Constant):
                    codes.add(str(keyword.value.value))

    assert codes, "expected to find raised application error codes"
    undocumented = codes - set(ERROR_TAXONOMY)
    assert not undocumented, f"error codes missing from ERROR_TAXONOMY: {sorted(undocumented)}"


def test_empty_input_has_a_complete_problem_pairing():
    assert "EMPTY_INPUT" in ERROR_TAXONOMY
    assert problem_type_for("EMPTY_INPUT", 422) == "urn:newslens:problem:empty-input"


# ------------------------------------------------------------------ readiness


def _override_service(*, db_ok: bool, ml_ok: bool) -> None:
    stub = SimpleNamespace(
        db=SimpleNamespace(ping=lambda: db_ok),
        ml_model=SimpleNamespace(is_ready=ml_ok),
        retriever=SimpleNamespace(records=[object()]),
    )
    app.dependency_overrides[get_news_service] = lambda: stub


def test_readiness_reports_503_when_a_core_dependency_is_unavailable(isolated_test_db):
    _override_service(db_ok=True, ml_ok=False)
    try:
        response = TestClient(app).get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_news_service, None)

    assert response.status_code == 503
    body = response.json()["data"]
    assert body["ready"] is False
    assert body["ml_model"] == "uninitialized"


def test_readiness_reports_200_when_healthy(isolated_test_db):
    _override_service(db_ok=True, ml_ok=True)
    try:
        response = TestClient(app).get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_news_service, None)

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["ready"] is True
    assert body["database"] == "connected"


# ------------------------------------------------------------- single-flight


def test_refresh_coordinator_allows_one_slot_per_key():
    key = "test:single-flight"
    assert refresh_coordinator.try_start(key) is True
    try:
        assert refresh_coordinator.try_start(key) is False
    finally:
        refresh_coordinator.finish(key)

    assert refresh_coordinator.try_start(key) is True
    refresh_coordinator.finish(key)


def test_concurrent_ingestion_refresh_is_rejected(isolated_test_db):
    key = "ingestion:refresh"
    assert refresh_coordinator.try_start(key) is True
    try:
        response = TestClient(app).post("/api/v1/ingestion/refresh", json={"source_type": "rss"})
    finally:
        refresh_coordinator.finish(key)

    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


# ------------------------------------------------------------------- metrics


def test_dashboard_does_not_fabricate_source_counts(isolated_test_db):
    service = get_news_service()
    with service.db._connect() as conn:
        conn.execute("DELETE FROM source_status")

    data = TestClient(app).get("/api/v1/dashboard/summary").json()["data"]
    assert data["total_configured_sources"] == 0
    assert data["active_sources_count"] == 0
