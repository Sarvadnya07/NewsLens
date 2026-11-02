"""BACKEND-03 adversarial validation: concurrency, duplication, integrity, security.

Every test here is a controlled experiment against a disposable database or an
in-memory stub. No real provider is called and no production database is opened.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.api.dependencies import get_news_service
from backend.main import app, refresh_coordinator
from src.models import NormalizedArticle
from src.storage.database import DatabaseManager

PROBLEM = "application/problem+json"
REMOTE = ("203.0.113.9", 51234)


def _article(
    index: int, *, title: str | None = None, source_type: str = "rss"
) -> NormalizedArticle:
    now = datetime.now(timezone.utc).isoformat()
    return NormalizedArticle(
        id=f"validate_{index:04d}",
        title=title or f"Validation article {index}",
        url=f"https://example.com/validation/{index}",
        publisher="Validation Wire",
        published_at=now,
        ingested_at=now,
        source_type=source_type,
        summary="Controlled validation fixture",
        language="en",
        country="IN",
        query="",
        origin="rss",
    )


def client(host: tuple[str, int] | None = None) -> TestClient:
    return TestClient(app) if host is None else TestClient(app, client=host)


# ============================================================== concurrency


def test_concurrent_identical_manual_submissions_create_one_row(isolated_test_db):
    payload = {
        "title": "Concurrent duplicate submission probe for municipal notices",
        "publisher": "Civic Wire",
        "url": "https://example.com/concurrent-duplicate-probe",
        "summary": "Ten clients submit the identical body at the same moment.",
    }
    ids: list[str] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(10)

    def submit() -> None:
        try:
            barrier.wait(timeout=10)
            response = TestClient(app).post("/api/v1/articles", json=payload)
            if response.status_code == 201:
                ids.append(response.json()["data"]["id"])
            else:
                errors.append(AssertionError(f"status {response.status_code}"))
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=submit) for _ in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, errors
    assert len(set(ids)) == 1, f"duplicate ids created: {set(ids)}"

    total = (
        TestClient(app)
        .get("/api/v1/articles?page=1&page_size=1")
        .json()["data"]["pagination"]["total_items"]
    )
    assert total == 33, f"expected 32 seeded + 1 submission, got {total}"


def test_concurrent_quota_reservations_never_exceed_budget(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "quota.db"))
    budget = 5
    outcomes: list[bool] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(12)

    def reserve() -> None:
        try:
            barrier.wait(timeout=10)
            allowed, _reason, _reservation = db.reserve_provider_budget(
                provider_id="newsdata_io",
                profile="validation",
                daily_budget=budget,
                rolling_15m_budget=20,
                min_interval_seconds=0,
                credits=1,
            )
            outcomes.append(allowed)
        except BaseException as exc:  # noqa: BLE001 - reported below
            errors.append(exc)

    threads = [threading.Thread(target=reserve) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, errors
    assert len(outcomes) == 12
    assert sum(1 for allowed in outcomes if allowed) == budget, (
        f"quota race: {sum(1 for a in outcomes if a)} reservations allowed for budget {budget}"
    )


def test_reads_and_writes_interleave_without_lock_errors(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "rw.db"))
    errors: list[BaseException] = []
    stop = threading.Event()

    def writer() -> None:
        try:
            for batch in range(15):
                db.upsert_articles(
                    [_article(batch * 10 + i) for i in range(10)],
                    status_rows=[
                        {
                            "source_name": "Validation Feed",
                            "source_type": "rss",
                            "status": "success",
                            "items_fetched": 10,
                            "is_active": 1,
                        }
                    ],
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            stop.set()

    def reader() -> None:
        try:
            while not stop.is_set():
                db.get_articles(limit=20)
                db.count_matching_articles(query="Validation")
                db.get_sources_distribution()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert not errors, errors
    assert db.get_article_count() == 150


# =========================================================== idempotency


def test_retry_after_timeout_does_not_duplicate_articles(tmp_path):
    """A client retry repeats the same content; the upsert must stay idempotent."""
    db = DatabaseManager(db_path=str(tmp_path / "retry.db"))
    article = _article(1)

    first = db.upsert_articles([article])
    second = db.upsert_articles([article])

    assert first == 1
    assert second == 0
    assert db.get_article_count() == 1


def test_discovery_records_are_deduplicated(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "disc.db"))
    db.upsert_articles([_article(1)])

    db.record_discovery("validate_0001", "newsdata_io", "ext-1", "india_publishers")
    db.record_discovery("validate_0001", "newsdata_io", "ext-1", "india_publishers")

    with db._connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM article_discoveries WHERE article_id = ? AND provider_id = ?",
            ("validate_0001", "newsdata_io"),
        ).fetchone()[0]
    assert count == 1


# ======================================================= database integrity


def test_not_null_and_primary_key_constraints_hold(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "constraints.db"))
    with db._connect() as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO articles (id) VALUES ('missing-required-fields')")


def test_cascade_delete_removes_child_discoveries(tmp_path):
    db = DatabaseManager(db_path=str(tmp_path / "cascade.db"))
    db.upsert_articles([_article(1)])
    db.record_discovery("validate_0001", "newsdata_io", "ext-1", "india_publishers")

    with db._connect() as conn:
        conn.execute("DELETE FROM articles WHERE id = ?", ("validate_0001",))

    with db._connect() as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM article_discoveries WHERE article_id = ?",
            ("validate_0001",),
        ).fetchone()[0]
    assert remaining == 0, "ON DELETE CASCADE is declared but did not fire"


def test_migrations_are_idempotent_on_reopen(tmp_path):
    path = str(tmp_path / "reopen.db")
    DatabaseManager(db_path=path)
    DatabaseManager(db_path=path)

    conn = sqlite3.connect(path)
    versions = [
        row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")
    ]
    conn.close()
    assert versions == [1, 2, 3, 4]


def test_concurrent_startup_does_not_crash_migrations(tmp_path):
    """Two processes booting at once must not collide on migration bookkeeping."""
    path = str(tmp_path / "startup.db")
    errors: list[BaseException] = []
    barrier = threading.Barrier(4)

    def boot() -> None:
        try:
            barrier.wait(timeout=10)
            DatabaseManager(db_path=path)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=boot) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors, f"concurrent startup failed: {errors}"


# ============================================================== security


def test_admin_key_comparison_rejects_wrong_values(isolated_test_db):
    with (
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setattr("backend.config.settings.APP_ENV", "production")
        mp.setattr("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999")
        for header in ("", "   ", "wrong_key_0000000", "prod_admin_secret_99"):
            response = client(REMOTE).post(
                "/api/v1/integrations/toi_national/test",
                headers={"X-Admin-Key": header},
            )
            assert response.status_code == 401, header
            assert response.headers["content-type"].startswith(PROBLEM)


def test_every_admin_endpoint_requires_authorization_in_production(isolated_test_db):
    targets = [
        ("post", "/api/v1/integrations/gdelt/test"),
        ("post", "/api/v1/integrations/gdelt/refresh"),
        ("post", "/api/v1/ingestion/refresh"),
    ]
    with (
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setattr("backend.config.settings.APP_ENV", "production")
        mp.setattr("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999")
        mp.setattr("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True)
        for method, path in targets:
            response = getattr(client(REMOTE), method)(path, json={})
            assert response.status_code == 401, f"{method.upper()} {path} -> {response.status_code}"
            assert response.json()["code"] == "UNAUTHORIZED"


def test_sql_injection_payloads_are_inert(isolated_test_db):
    c = client()
    for payload in (
        "' OR 1=1 --",
        "'; DROP TABLE articles;--",
        "1' UNION SELECT * FROM articles--",
    ):
        response = c.get("/api/v1/articles", params={"query": payload})
        assert response.status_code == 200
        assert response.json()["data"]["pagination"]["total_items"] == 0

        detail = c.get(f"/api/v1/articles/{payload}")
        assert detail.status_code == 404

    # Tables are intact.
    assert c.get("/api/v1/articles").json()["data"]["pagination"]["total_items"] == 32


def test_like_wildcards_are_escaped_not_interpreted(isolated_test_db):
    c = client()
    for wildcard in ("%", "_", "%%"):
        body = c.get("/api/v1/articles", params={"query": wildcard}).json()["data"]
        assert body["pagination"]["total_items"] == 0, f"{wildcard!r} matched as a wildcard"

    assert c.get("/api/v1/articles", params={"query": "railway"}).status_code == 200


def test_source_type_is_parameterised_not_concatenated(isolated_test_db):
    body = client().get("/api/v1/articles", params={"source_type": "rss' OR '1'='1"}).json()["data"]
    assert body["pagination"]["total_items"] == 0


def test_path_traversal_article_id_is_not_found(isolated_test_db):
    response = client().get("/api/v1/articles/..%2F..%2Fetc%2Fpasswd")
    # Whatever the router does with the encoded slashes, the invariant is that no
    # traversal succeeds: never 200, never 500, always a structured problem.
    assert response.status_code == 404, response.status_code
    assert response.headers["content-type"].startswith(PROBLEM)
    assert "root:" not in response.text


def test_oversized_request_id_is_replaced(isolated_test_db):
    response = client().get("/api/v1/health", headers={"X-Request-ID": "A" * 500})
    assert len(response.headers["X-Request-ID"]) == 32


def test_sensitive_values_never_appear_in_error_bodies(isolated_test_db):
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("backend.config.settings.APP_ENV", "production")
        mp.setattr("backend.config.settings.ADMIN_API_KEY", "prod_admin_secret_999")
        response = client(REMOTE).post(
            "/api/v1/integrations/gdelt/test",
            headers={"X-Admin-Key": "leaked-guess-value"},
        )

    body = response.text
    assert "prod_admin_secret_999" not in body
    assert "leaked-guess-value" not in body
    assert "Traceback" not in body


# ========================================================= rate limiting


def test_rate_limit_rejects_and_recovers(isolated_test_db):
    c = client()
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("backend.config.settings.APP_ENV", "development")
        mp.setattr("backend.config.settings.ADMIN_RATE_LIMIT_PER_MINUTE", 2)
        mp.setattr("backend.config.settings.REQUIRE_ADMIN_AUTH_FOR_INGESTION", True)
        from src.ingestion.models import RefreshResult

        def _noop_refresh(_self):
            return RefreshResult(
                total_fetched=0,
                new_stored=0,
                duration_ms=0.0,
                provider_results={},
                all_succeeded=True,
                all_failed=False,
            )

        mp.setattr("src.services.news_service.NewsLensService.refresh_rss_feeds", _noop_refresh)
        statuses = []
        for _ in range(3):
            statuses.append(
                c.post("/api/v1/ingestion/refresh", json={"source_type": "rss"}).status_code
            )
        limited = c.post("/api/v1/ingestion/refresh", json={"source_type": "rss"})

    assert statuses[0] == 200
    assert 429 in statuses or limited.status_code == 429
    from backend.main import reset_rate_limits

    reset_rate_limits()
    assert client().get("/api/v1/health").status_code == 200


# ================================================== health / shutdown / cache


def test_drain_waits_for_active_work_then_reports_clean():
    key = "validation:drain"
    assert refresh_coordinator.try_start(key)
    try:
        assert refresh_coordinator.drain(timeout_seconds=0.1) is False
        threading.Timer(0.15, lambda: refresh_coordinator.finish(key)).start()
        assert refresh_coordinator.drain(timeout_seconds=3.0) is True
    finally:
        refresh_coordinator.finish(key)


def test_cluster_cache_is_invalidated_by_writes(isolated_test_db):
    service = get_news_service()
    first = service.get_cached_coverage_clusters(sample_limit=50)
    service.submit_manual_article(
        title="Cache invalidation probe on district transport notices",
        url="https://example.com/cache-invalidation-probe",
    )
    second = service.get_cached_coverage_clusters(sample_limit=50)

    assert second is not first, "write did not invalidate the coverage cache"


def test_repeated_operations_do_not_leak_handles(tmp_path):
    psutil = pytest.importorskip("psutil")
    db = DatabaseManager(db_path=str(tmp_path / "handles.db"))
    process = psutil.Process(os.getpid())

    def handle_count() -> int:
        return (
            process.num_handles() if hasattr(process, "num_handles") else len(process.open_files())
        )

    for _ in range(20):
        db.get_article_count()
    baseline = handle_count()

    for _ in range(300):
        db.get_article_count()
        db.get_articles(limit=5)

    assert handle_count() - baseline < 25, "connection handles are leaking"
