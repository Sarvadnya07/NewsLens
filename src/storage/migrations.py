"""Database schema migration engine for NewsLens India.

Provides versioned, additive, idempotent migrations with provenance tracking
in the `schema_migrations` table.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable, List, Tuple

logger = logging.getLogger(__name__)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Checks if a table exists in SQLite master."""
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Returns set of column names for a given SQLite table."""
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1] for row in cursor.fetchall()}
    except sqlite3.Error:
        return set()


def _migration_001_add_origin_and_telemetry(conn: sqlite3.Connection) -> None:
    """Migration 001:
    - Add persistent 'origin' column to articles with index if table exists.
    - Backfill 'origin' from source_type and preserve manual submissions.
    - Add operational telemetry columns to source_status table if table exists.
    - Mark retired sources (e.g. Deccan Herald) as inactive (is_active=0).
    """
    cursor = conn.cursor()

    # 1. Update articles table if present
    if _table_exists(conn, "articles"):
        article_cols = _get_table_columns(conn, "articles")
        if "origin" not in article_cols:
            logger.info("Adding 'origin' column to articles table")
            cursor.execute("ALTER TABLE articles ADD COLUMN origin TEXT NOT NULL DEFAULT 'unknown'")

        # Backfill origin with explicit, validated source_type mapping
        cursor.execute("""
            UPDATE articles
            SET origin = CASE
                WHEN source_type = 'rss' THEN 'rss'
                WHEN source_type = 'gdelt' THEN 'gdelt'
                WHEN source_type = 'manual' THEN 'manual'
                ELSE 'unknown'
            END
            WHERE origin IS NULL OR origin = 'unknown' OR origin = ''
        """)
        # Specifically protect manual user submissions
        cursor.execute("""
            UPDATE articles
            SET origin = 'manual'
            WHERE id LIKE 'manual_%' OR source_type = 'manual'
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_origin ON articles(origin)")

    # 2. Update source_status table if present
    if _table_exists(conn, "source_status"):
        source_cols = _get_table_columns(conn, "source_status")
        telemetry_columns = [
            ("last_attempt_at", "TEXT"),
            ("last_attempt_status", "TEXT"),
            ("last_successful_refresh_at", "TEXT"),
            ("last_http_status", "INTEGER"),
            ("last_latency_ms", "REAL"),
            ("new_items_inserted", "INTEGER DEFAULT 0"),
            ("is_active", "INTEGER DEFAULT 1"),
        ]

        for col_name, col_def in telemetry_columns:
            if col_name not in source_cols:
                logger.info("Adding '%s' column to source_status table", col_name)
                cursor.execute(f"ALTER TABLE source_status ADD COLUMN {col_name} {col_def}")

        # Backfill telemetry fields from existing columns
        cursor.execute("""
            UPDATE source_status
            SET last_attempt_at = COALESCE(last_attempt_at, last_refresh_at)
            WHERE last_attempt_at IS NULL
        """)
        cursor.execute("""
            UPDATE source_status
            SET last_attempt_status = COALESCE(last_attempt_status, status)
            WHERE last_attempt_status IS NULL
        """)
        cursor.execute("""
            UPDATE source_status
            SET last_successful_refresh_at = CASE
                WHEN status = 'success' THEN COALESCE(last_successful_refresh_at, last_refresh_at)
                ELSE last_successful_refresh_at
            END
            WHERE last_successful_refresh_at IS NULL AND status = 'success'
        """)
        cursor.execute("""
            UPDATE source_status
            SET is_active = CASE
                WHEN source_name LIKE '%Deccan%' THEN 0
                ELSE 1
            END
        """)


def _migration_002_add_discoveries_and_quotas(conn: sqlite3.Connection) -> None:
    """Migration 002:
    - Add 'article_discoveries' table for multi-provider provenance tracking.
    - Add 'provider_request_log' table for persistent quota governance.
    - Backfill initial discovery events for existing articles.
    """
    cursor = conn.cursor()

    # 1. Multi-provider provenance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_discoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT NOT NULL,
            provider_id TEXT NOT NULL,
            provider_article_id TEXT,
            discovery_profile TEXT NOT NULL DEFAULT 'default',
            discovered_at TEXT NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_discoveries_art ON article_discoveries(article_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_discoveries_prov ON article_discoveries(provider_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_discoveries_prof ON article_discoveries(discovery_profile)"
    )
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_discoveries_unique_event ON article_discoveries(article_id, provider_id, discovery_profile)"
    )

    # 2. Persistent quota request log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS provider_request_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id TEXT NOT NULL,
            profile TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            status_code INTEGER,
            outcome TEXT NOT NULL,
            credits_consumed INTEGER DEFAULT 1,
            latency_ms REAL
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_reqlog_prov_time ON provider_request_log(provider_id, requested_at)"
    )

    # 3. Additive backfill for existing articles
    if _table_exists(conn, "articles"):
        cursor.execute("""
            INSERT INTO article_discoveries (article_id, provider_id, provider_article_id, discovery_profile, discovered_at, metadata_json)
            SELECT
                id,
                CASE
                    WHEN origin = 'rss' THEN 'rss_syndicate'
                    WHEN origin = 'gdelt' THEN 'gdelt_doc_api'
                    WHEN origin = 'newsdata' THEN 'newsdata_io'
                    WHEN origin = 'manual' THEN 'manual_submission'
                    ELSE origin
                END,
                id,
                'initial_ingest',
                ingested_at,
                '{}'
            FROM articles
            WHERE id NOT IN (SELECT article_id FROM article_discoveries)
        """)


def _migration_003_add_fact_check_claims(conn: sqlite3.Connection) -> None:
    """Migration 003:
    - Add 'fact_check_claims' table for storing ClaimReview evidence records independently of news articles.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fact_check_claims (
            id TEXT PRIMARY KEY,
            claim_text TEXT NOT NULL,
            claimant TEXT,
            claim_date TEXT,
            rating_text TEXT,
            rating_standardized TEXT,
            publisher_name TEXT NOT NULL,
            publisher_site TEXT,
            fact_check_url TEXT NOT NULL,
            review_date TEXT,
            language_code TEXT,
            matched_article_id TEXT,
            retrieved_at TEXT NOT NULL,
            raw_metadata TEXT,
            FOREIGN KEY(matched_article_id) REFERENCES articles(id) ON DELETE SET NULL
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fc_matched ON fact_check_claims(matched_article_id)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fc_pub ON fact_check_claims(publisher_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_fc_time ON fact_check_claims(retrieved_at)")


def _migration_004_add_effective_date_index(conn: sqlite3.Connection) -> None:
    """Migration 004:
    - Add an expression index matching the effective-date ordering used by every
      article listing. Without it, ORDER BY falls back to a full scan plus a
      temporary B-tree, which grows linearly with the article ledger.
    """
    cursor = conn.cursor()
    if _table_exists(conn, "articles"):
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_effective_date "
            "ON articles(COALESCE(NULLIF(published_at, ''), ingested_at) DESC, id ASC)"
        )


MIGRATION_REGISTRY: List[Tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "001_add_origin_and_telemetry", _migration_001_add_origin_and_telemetry),
    (2, "002_add_discoveries_and_quotas", _migration_002_add_discoveries_and_quotas),
    (3, "003_add_fact_check_claims", _migration_003_add_fact_check_claims),
    (4, "004_add_effective_date_index", _migration_004_add_effective_date_index),
]


def init_migration_table(conn: sqlite3.Connection) -> None:
    """Ensures the schema_migrations tracking table exists."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)


def get_applied_migrations(conn: sqlite3.Connection) -> List[int]:
    """Returns list of migration versions already applied to the database."""
    init_migration_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
    return [row[0] for row in cursor.fetchall()]


def run_migrations(conn: sqlite3.Connection) -> List[int]:
    """Runs all pending migrations in order under a single write lock.

    Concurrent startups (several workers, or a restart overlapping another
    process) must not both decide a migration is unapplied. ``BEGIN IMMEDIATE``
    makes the applied-version read and the DDL one critical section, so a second
    process waits, then observes the committed versions and skips them.

    Returns list of migration versions applied in this invocation.
    """
    init_migration_table(conn)

    # Release any implicitly opened transaction so the lock can be taken explicitly.
    if conn.in_transaction:
        conn.commit()

    conn.execute("BEGIN IMMEDIATE")
    try:
        applied = set(get_applied_migrations(conn))
        applied_now: List[int] = []

        for version, name, migration_func in MIGRATION_REGISTRY:
            if version in applied:
                continue

            logger.info("Applying database migration %03d: %s", version, name)
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor = conn.cursor()
            cursor.execute(f"SAVEPOINT migration_{version}")
            try:
                migration_func(conn)
                cursor.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (version, name, now_iso),
                )
                cursor.execute(f"RELEASE SAVEPOINT migration_{version}")
                applied.add(version)
                applied_now.append(version)
            except Exception:
                cursor.execute(f"ROLLBACK TO SAVEPOINT migration_{version}")
                logger.exception("Migration %03d (%s) failed and was rolled back", version, name)
                raise

        conn.commit()
        return applied_now
    except Exception:
        conn.rollback()
        raise
