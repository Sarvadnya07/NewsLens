"""SQLite database persistence for NewsLens India.

Stores normalized articles and per-source ingestion-status snapshots.
Provides idempotent batch upserts, literal LIKE search escaping, pagination,
WAL mode, busy-timeout handling, and transaction boundaries.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional

from src.ingestion.models import VALID_PROVIDER_STATUSES
from src.models import NormalizedArticle, normalize_published_at
from src.storage.migrations import run_migrations

logger = logging.getLogger(__name__)

# Publication timestamps are normalized on write, but older rows may still hold
# raw feed text. Filtering and ordering therefore use a single effective date:
# the publication date when it is present, otherwise the ingestion date.
EFFECTIVE_DATE_SQL = "COALESCE(NULLIF(published_at, ''), ingested_at)"

# Base statements are constants so the only dynamic part is a fixed set of generated
# filter fragments; every value is still bound as a SQL parameter.
SELECT_ARTICLES_SQL = "SELECT * FROM articles WHERE 1=1"
COUNT_ARTICLES_SQL = "SELECT COUNT(*) FROM articles WHERE 1=1"

ORDER_COLUMNS = {
    "ingested_at": "ingested_at",
    "published_at": EFFECTIVE_DATE_SQL,
    "title": "title",
}


def escape_like_literal(s: str, escape_char: str = "\\") -> str:
    """Escapes SQLite LIKE wildcards (% and _) and the escape character itself."""
    if not s:
        return ""
    s = s.replace(escape_char, escape_char + escape_char)
    s = s.replace("%", escape_char + "%")
    s = s.replace("_", escape_char + "_")
    return s


class DatabaseManager:
    """Thread-safe SQLite manager for normalized news articles and source health."""

    def __init__(self, db_path: str = "data/newslens.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Opens a connection and guarantees commit/rollback and closure.

        ``with sqlite3.connect(...)`` only manages the transaction; the handle
        itself stays open until garbage collection. Repeated ingestion runs
        leaked file handles, which is visible on Windows, so every call site
        uses this context manager instead.
        """
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    published_at TEXT,
                    ingested_at TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    summary TEXT,
                    language TEXT,
                    country TEXT,
                    query TEXT,
                    raw_metadata TEXT,
                    origin TEXT NOT NULL DEFAULT 'unknown'
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_published
                ON articles(published_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_source
                ON articles(source_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_query
                ON articles(query)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_ingested
                ON articles(ingested_at DESC)
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS source_status (
                    source_name TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    last_refresh_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_fetched INTEGER DEFAULT 0,
                    error_message TEXT,
                    last_attempt_at TEXT,
                    last_attempt_status TEXT,
                    last_successful_refresh_at TEXT,
                    last_http_status INTEGER,
                    last_latency_ms REAL,
                    new_items_inserted INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
            # Execute versioned additive migrations
            run_migrations(conn)

    def upsert_article(self, article: NormalizedArticle) -> bool:
        """Inserts or updates a normalized article.

        Returns True if a new row was inserted, False if an existing row was updated.
        """
        raw_meta_json = json.dumps(article.raw_metadata or {})
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    # Check if row exists to accurately return inserted vs updated
                    cursor.execute("SELECT id FROM articles WHERE id = ?", (article.id,))
                    exists = cursor.fetchone() is not None

                    origin_val = (
                        article.origin
                        if article.origin in ("rss", "gdelt", "newsdata", "manual", "unknown")
                        else (
                            article.source_type
                            if article.source_type in ("rss", "gdelt", "newsdata", "manual")
                            else "unknown"
                        )
                    )
                    cursor.execute(
                        """
                        INSERT INTO articles (
                            id, title, url, publisher, published_at, ingested_at,
                            source_type, summary, language, country, query, raw_metadata, origin
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            title=excluded.title,
                            url=excluded.url,
                            publisher=excluded.publisher,
                            published_at=excluded.published_at,
                            summary=excluded.summary,
                            query=excluded.query,
                            raw_metadata=excluded.raw_metadata,
                            origin=excluded.origin
                        """,
                        (
                            article.id,
                            article.title.strip() or "Untitled",
                            article.url or "",
                            article.publisher.strip() or "Unknown",
                            article.published_at or "",
                            article.ingested_at,
                            article.source_type,
                            article.summary or "",
                            article.language or "en",
                            article.country or "IN",
                            article.query or "",
                            raw_meta_json,
                            origin_val,
                        ),
                    )
                    # Additive provenance tracking
                    prov_id = (
                        "newsdata_io"
                        if article.source_type == "newsdata"
                        else (
                            "gdelt_doc_api"
                            if article.source_type == "gdelt"
                            else (
                                "currents"
                                if article.source_type == "currents"
                                else (
                                    "guardian_open_platform"
                                    if article.source_type == "guardian"
                                    else (
                                        str(article.raw_metadata.get("feed_id", "rss_syndicate"))
                                        if article.source_type == "rss"
                                        else "manual_submission"
                                    )
                                )
                            )
                        )
                    )
                    prof = str(article.raw_metadata.get("discovery_profile", "default"))
                    p_art_id = str(article.raw_metadata.get("article_id") or "")
                    cursor.execute(
                        """
                        INSERT INTO article_discoveries (
                            article_id, provider_id, provider_article_id, discovery_profile, discovered_at, metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(article_id, provider_id, discovery_profile) DO UPDATE SET
                            provider_article_id = COALESCE(NULLIF(excluded.provider_article_id, ''), article_discoveries.provider_article_id),
                            metadata_json = excluded.metadata_json
                        """,
                        (
                            article.id,
                            prov_id,
                            p_art_id,
                            prof,
                            datetime.now(timezone.utc).isoformat(),
                            raw_meta_json,
                        ),
                    )
                    conn.commit()
                    return not exists
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    if attempt < max_attempts - 1:
                        time.sleep(0.05 * (2**attempt))
                        continue
                raise

        return False

    def upsert_articles(self, articles: List[NormalizedArticle]) -> int:
        """Batch upserts normalized articles inside a single transaction.

        Returns the count of newly inserted articles (ignoring updates).
        """
        if not articles:
            return 0

        inserted_count = 0
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                with self._connect() as conn:
                    cursor = conn.cursor()
                    for article in articles:
                        cursor.execute("SELECT id FROM articles WHERE id = ?", (article.id,))
                        exists = cursor.fetchone() is not None

                        raw_meta_json = json.dumps(article.raw_metadata or {})
                        origin_val = (
                            article.origin
                            if article.origin in ("rss", "gdelt", "newsdata", "manual", "unknown")
                            else (
                                article.source_type
                                if article.source_type in ("rss", "gdelt", "newsdata", "manual")
                                else "unknown"
                            )
                        )
                        cursor.execute(
                            """
                            INSERT INTO articles (
                                id, title, url, publisher, published_at, ingested_at,
                                source_type, summary, language, country, query, raw_metadata, origin
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                title=excluded.title,
                                url=excluded.url,
                                publisher=excluded.publisher,
                                published_at=excluded.published_at,
                                summary=excluded.summary,
                                query=excluded.query,
                                raw_metadata=excluded.raw_metadata,
                                origin=excluded.origin
                            """,
                            (
                                article.id,
                                article.title.strip() or "Untitled",
                                article.url or "",
                                article.publisher.strip() or "Unknown",
                                article.published_at or "",
                                article.ingested_at,
                                article.source_type,
                                article.summary or "",
                                article.language or "en",
                                article.country or "IN",
                                article.query or "",
                                raw_meta_json,
                                origin_val,
                            ),
                        )
                        # Additive provenance tracking
                        prov_id = (
                            "newsdata_io"
                            if article.source_type == "newsdata"
                            else (
                                "gdelt_doc_api"
                                if article.source_type == "gdelt"
                                else (
                                    "currents"
                                    if article.source_type == "currents"
                                    else (
                                        "guardian_open_platform"
                                        if article.source_type == "guardian"
                                        else (
                                            str(
                                                article.raw_metadata.get("feed_id", "rss_syndicate")
                                            )
                                            if article.source_type == "rss"
                                            else "manual_submission"
                                        )
                                    )
                                )
                            )
                        )
                        prof = str(article.raw_metadata.get("discovery_profile", "default"))
                        p_art_id = str(article.raw_metadata.get("article_id") or "")
                        cursor.execute(
                            """
                            INSERT INTO article_discoveries (
                                article_id, provider_id, provider_article_id, discovery_profile, discovered_at, metadata_json
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(article_id, provider_id, discovery_profile) DO UPDATE SET
                                provider_article_id = COALESCE(NULLIF(excluded.provider_article_id, ''), article_discoveries.provider_article_id),
                                metadata_json = excluded.metadata_json
                            """,
                            (
                                article.id,
                                prov_id,
                                p_art_id,
                                prof,
                                datetime.now(timezone.utc).isoformat(),
                                raw_meta_json,
                            ),
                        )
                        if not exists:
                            inserted_count += 1
                    conn.commit()
                return inserted_count
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    if attempt < max_attempts - 1:
                        time.sleep(0.05 * (2**attempt))
                        continue
                raise

        return inserted_count

    @staticmethod
    def _build_filters(
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        publisher: Optional[str] = None,
        since_iso: Optional[str] = None,
        discovery_profile: Optional[str] = None,
    ) -> tuple[str, List[Any]]:
        """Builds the shared WHERE clause used by listing and counting queries."""
        clause = ""
        params: List[Any] = []

        if source_type:
            clause += " AND source_type = ?"
            params.append(source_type)

        if discovery_profile:
            clause += " AND id IN (SELECT article_id FROM article_discoveries WHERE discovery_profile = ?)"
            params.append(discovery_profile)

        if publisher:
            clause += " AND publisher = ?"
            params.append(publisher)

        if since_iso:
            clause += f" AND {EFFECTIVE_DATE_SQL} >= ?"
            params.append(since_iso)

        if query and query.strip():
            escaped = escape_like_literal(query.strip())
            wildcard = f"%{escaped}%"
            clause += (
                " AND (title LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\'"
                " OR query LIKE ? ESCAPE '\\' OR publisher LIKE ? ESCAPE '\\')"
            )
            params.extend([wildcard, wildcard, wildcard, wildcard])

        return clause, params

    def get_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "ingested_at",
        ascending: bool = False,
        publisher: Optional[str] = None,
        since_iso: Optional[str] = None,
        discovery_profile: Optional[str] = None,
    ) -> List[NormalizedArticle]:
        """Retrieves articles with parameterized filtering, safe LIKE wildcards, and pagination."""
        with self._connect() as conn:
            cursor = conn.cursor()
            clause, params = self._build_filters(
                query, source_type, publisher, since_iso, discovery_profile
            )
            sql = SELECT_ARTICLES_SQL + clause

            direction = "ASC" if ascending else "DESC"
            col = ORDER_COLUMNS.get(order_by, "ingested_at")
            sql += f" ORDER BY {col} {direction}, id ASC LIMIT ? OFFSET ?"
            params.extend([max(limit, 1), max(offset, 0)])

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            result: List[NormalizedArticle] = []
            for r in rows:
                raw_meta = {}
                if r["raw_metadata"]:
                    try:
                        raw_meta = json.loads(r["raw_metadata"])
                    except Exception as e:
                        logger.debug("Failed to decode raw_metadata for article %s: %s", r["id"], e)
                result.append(
                    NormalizedArticle(
                        id=r["id"],
                        title=r["title"],
                        url=r["url"],
                        publisher=r["publisher"],
                        published_at=r["published_at"] or "",
                        ingested_at=r["ingested_at"],
                        source_type=r["source_type"],
                        summary=r["summary"] or "",
                        language=r["language"] or "en",
                        country=r["country"] or "IN",
                        query=r["query"] or "",
                        raw_metadata=raw_meta,
                        origin=r["origin"]
                        if "origin" in r.keys() and r["origin"]
                        else (
                            r["source_type"]
                            if r["source_type"] in ("rss", "gdelt", "newsdata", "manual")
                            else "unknown"
                        ),
                    )
                )
            return result

    def count_matching_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        publisher: Optional[str] = None,
        since_iso: Optional[str] = None,
        discovery_profile: Optional[str] = None,
    ) -> int:
        """Total matching records, independent of the page size in use."""
        with self._connect() as conn:
            cursor = conn.cursor()
            clause, params = self._build_filters(
                query, source_type, publisher, since_iso, discovery_profile
            )
            cursor.execute(COUNT_ARTICLES_SQL + clause, params)
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def get_distinct_publishers(self) -> List[str]:
        """Returns the publishers actually present in the datastore, most common first."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT publisher, COUNT(*) AS n FROM articles
                WHERE publisher IS NOT NULL AND TRIM(publisher) != ''
                GROUP BY publisher ORDER BY n DESC, publisher ASC
                """
            )
            return [row["publisher"] for row in cursor.fetchall()]

    def normalize_published_timestamps(self) -> Dict[str, int]:
        """Rewrites legacy non-normalized publication timestamps in place.

        Idempotent maintenance step: rows already stored as ISO-8601 UTC are
        left untouched. Returns counts so the caller can report the migration.
        """
        updated = 0
        cleared = 0
        with self._connect() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT id, published_at FROM articles").fetchall()
            for row in rows:
                stored = row["published_at"] or ""
                normalized = normalize_published_at(stored)
                if normalized == stored:
                    continue
                cursor.execute(
                    "UPDATE articles SET published_at = ? WHERE id = ?", (normalized, row["id"])
                )
                updated += 1
                if stored and not normalized:
                    cleared += 1
        if updated:
            logger.info(
                "Normalized %d publication timestamp(s); %d unparseable value(s) cleared",
                updated,
                cleared,
            )
        return {"updated": updated, "cleared": cleared, "scanned": len(rows)}

    def get_article_count(self) -> int:
        """Returns the total number of articles in the datastore."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def get_article_by_id(self, article_id: str) -> Optional[NormalizedArticle]:
        """Retrieves a single article by its unique ID."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
            r = cursor.fetchone()
            if not r:
                return None
            raw_meta = {}
            if r["raw_metadata"]:
                try:
                    raw_meta = json.loads(r["raw_metadata"])
                except Exception as e:
                    logger.debug("Failed to decode raw_metadata for article %s: %s", r["id"], e)
            return NormalizedArticle(
                id=r["id"],
                title=r["title"],
                url=r["url"],
                publisher=r["publisher"],
                published_at=r["published_at"] or "",
                ingested_at=r["ingested_at"],
                source_type=r["source_type"],
                summary=r["summary"] or "",
                language=r["language"] or "en",
                country=r["country"] or "IN",
                query=r["query"] or "",
                raw_metadata=raw_meta,
                origin=r["origin"] if "origin" in r.keys() and r["origin"] else "ingested",
            )

    def record_source_status(
        self,
        source_name: str,
        source_type: str,
        status: str,
        items_fetched: int = 0,
        error_message: Optional[str] = None,
        http_status: Optional[int] = None,
        latency_ms: Optional[float] = None,
        new_items_inserted: int = 0,
        is_active: Optional[int] = None,
    ) -> None:
        """Records or updates the last known outcome and operational telemetry for a source.

        Preserves existing last_successful_refresh_at if current attempt did not succeed.
        """
        now = datetime.now(timezone.utc).isoformat()
        clean_status = status if status in VALID_PROVIDER_STATUSES else "provider_unavailable"
        last_successful = now if clean_status == "success" else None

        # Retired sources remain inactive
        active_val = 0 if "Deccan" in source_name else (1 if is_active is None else int(is_active))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO source_status (
                    source_name, source_type, last_refresh_at, status, items_fetched, error_message,
                    last_attempt_at, last_attempt_status, last_successful_refresh_at,
                    last_http_status, last_latency_ms, new_items_inserted, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name) DO UPDATE SET
                    source_type=excluded.source_type,
                    last_refresh_at=excluded.last_refresh_at,
                    status=excluded.status,
                    items_fetched=excluded.items_fetched,
                    error_message=excluded.error_message,
                    last_attempt_at=excluded.last_attempt_at,
                    last_attempt_status=excluded.last_attempt_status,
                    last_successful_refresh_at=COALESCE(excluded.last_successful_refresh_at, source_status.last_successful_refresh_at),
                    last_http_status=excluded.last_http_status,
                    last_latency_ms=excluded.last_latency_ms,
                    new_items_inserted=excluded.new_items_inserted,
                    is_active=excluded.is_active
                """,
                (
                    source_name,
                    source_type,
                    now,
                    clean_status,
                    items_fetched,
                    error_message,
                    now,
                    clean_status,
                    last_successful,
                    http_status,
                    latency_ms,
                    new_items_inserted,
                    active_val,
                ),
            )
            conn.commit()

    def get_source_status(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Returns recorded status and telemetry for a specific source."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM source_status WHERE source_name = ?", (source_name,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_source_status(self) -> List[Dict[str, Any]]:
        """Returns all recorded source statuses ordered by most recent refresh."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM source_status ORDER BY last_refresh_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    def get_sources_distribution(self) -> Dict[str, int]:
        """Returns article count grouped by source_type computed directly in SQLite."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COALESCE(NULLIF(source_type, ''), 'unknown') AS src, COUNT(*) AS cnt
                FROM articles
                GROUP BY src
                ORDER BY cnt DESC
                """
            )
            return {row["src"]: int(row["cnt"]) for row in cursor.fetchall()}

    def get_publishers_distribution(self, limit: int = 10) -> Dict[str, int]:
        """Returns top publisher distribution computed directly in SQLite."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT publisher, COUNT(*) AS cnt
                FROM articles
                WHERE publisher IS NOT NULL AND TRIM(publisher) != ''
                GROUP BY publisher
                ORDER BY cnt DESC, publisher ASC
                LIMIT ?
                """,
                (max(int(limit), 1),),
            )
            return {row["publisher"]: int(row["cnt"]) for row in cursor.fetchall()}

    def get_active_source_count(self) -> int:
        """Returns count of active configured sources whose last attempt was successful."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM source_status WHERE is_active = 1 AND status = 'success'"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def get_total_configured_sources_count(self) -> int:
        """Returns count of active configured sources (excluding retired sources)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM source_status WHERE is_active = 1")
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    # --- Multi-Provider Provenance & Discovery Tracking ---

    def record_discovery(
        self,
        article_id: str,
        provider_id: str,
        provider_article_id: Optional[str] = None,
        discovery_profile: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Records an individual discovery event for an article in an idempotent manner."""
        meta_json = json.dumps(metadata or {})
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO article_discoveries (
                    article_id, provider_id, provider_article_id, discovery_profile, discovered_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id, provider_id, discovery_profile) DO UPDATE SET
                    provider_article_id = COALESCE(NULLIF(excluded.provider_article_id, ''), article_discoveries.provider_article_id),
                    metadata_json = excluded.metadata_json
                """,
                (
                    article_id,
                    provider_id,
                    provider_article_id or "",
                    discovery_profile,
                    now_iso,
                    meta_json,
                ),
            )
            conn.commit()

    def get_article_discoveries(self, article_id: str) -> List[Dict[str, Any]]:
        """Retrieves all recorded discovery events for a specific article."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, article_id, provider_id, provider_article_id, discovery_profile, discovered_at, metadata_json
                FROM article_discoveries
                WHERE article_id = ?
                ORDER BY discovered_at ASC
                """,
                (article_id,),
            )
            rows = cursor.fetchall()
            result = []
            for r in rows:
                meta = {}
                if r["metadata_json"]:
                    try:
                        meta = json.loads(r["metadata_json"])
                    except Exception:
                        pass
                result.append(
                    {
                        "id": r["id"],
                        "article_id": r["article_id"],
                        "provider_id": r["provider_id"],
                        "provider_article_id": r["provider_article_id"],
                        "discovery_profile": r["discovery_profile"],
                        "discovered_at": r["discovered_at"],
                        "metadata": meta,
                    }
                )
            return result

    # --- Quota Governance & Request Budgeting ---

    def record_provider_request(
        self,
        provider_id: str,
        profile: str,
        status_code: Optional[int],
        outcome: str,
        credits_consumed: int = 1,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Logs an outgoing API provider request into persistent SQLite audit table."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO provider_request_log (
                    provider_id, profile, requested_at, status_code, outcome, credits_consumed, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    provider_id,
                    profile,
                    now_iso,
                    status_code,
                    outcome,
                    credits_consumed,
                    latency_ms or 0.0,
                ),
            )
            conn.commit()

    def check_provider_budget(
        self,
        provider_id: str = "newsdata_io",
        profile: str = "default",
        daily_budget: int = 50,
        rolling_15m_budget: int = 10,
        min_interval_seconds: float = 60.0,
    ) -> tuple[bool, Optional[str]]:
        """Verifies whether an outgoing provider request complies with persistent quota budgets.

        Read-only verification without making a reservation.
        """
        now = datetime.now(timezone.utc)
        iso_24h = (now - timedelta(days=1)).isoformat()
        iso_15m = (now - timedelta(minutes=15)).isoformat()
        # Safe reservation lease (300s / 5 minutes) bounding maximum HTTP request and retry durations
        iso_stale_cutoff = (now - timedelta(seconds=300)).isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()

            # 1. Daily budget check (completed dispatched calls + active unexpired reservations)
            cursor.execute(
                """
                SELECT COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_24h, iso_stale_cutoff),
            )
            daily_used = cursor.fetchone()[0]
            if daily_used >= daily_budget:
                return (
                    False,
                    f"Daily request budget reached ({daily_used}/{daily_budget}). Request blocked.",
                )

            # 2. Rolling 15-minute budget check
            cursor.execute(
                """
                SELECT COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_15m, iso_stale_cutoff),
            )
            used_15m = cursor.fetchone()[0]
            if used_15m >= rolling_15m_budget:
                return (
                    False,
                    f"Rolling 15-minute budget reached ({used_15m}/{rolling_15m_budget}). Please wait.",
                )

            # 3. Minimum refresh interval for this profile
            if min_interval_seconds > 0:
                cursor.execute(
                    """
                    SELECT requested_at FROM provider_request_log
                    WHERE provider_id = ? AND profile = ?
                      AND outcome != 'canceled'
                    ORDER BY requested_at DESC LIMIT 1
                    """,
                    (provider_id, profile),
                )
                last_row = cursor.fetchone()
                if last_row and last_row[0]:
                    try:
                        last_time = datetime.fromisoformat(last_row[0])
                        if last_time.tzinfo is None:
                            last_time = last_time.replace(tzinfo=timezone.utc)
                        elapsed = (now - last_time).total_seconds()
                        if elapsed < min_interval_seconds:
                            return (
                                False,
                                f"Minimum interval between {profile} refreshes not elapsed ({elapsed:.1f}s < {min_interval_seconds:.0f}s).",
                            )
                    except Exception:
                        pass

        return True, None

    def reserve_provider_budget(
        self,
        provider_id: str = "newsdata_io",
        profile: str = "default",
        daily_budget: int = 50,
        rolling_15m_budget: int = 10,
        min_interval_seconds: float = 60.0,
        credits: int = 1,
    ) -> tuple[bool, Optional[str], Optional[int]]:
        """Atomically checks quota budgets and reserves a request row across processes.

        Guarantees that simultaneous requests across multiple Uvicorn workers or
        separate processes cannot exceed daily or 15-minute quota limits.

        Returns:
            (allowed: bool, reason_if_blocked: Optional[str], reservation_id: Optional[int])
        """
        now = datetime.now(timezone.utc)
        iso_24h = (now - timedelta(days=1)).isoformat()
        iso_15m = (now - timedelta(minutes=15)).isoformat()
        # Safe reservation lease (300s / 5 minutes) bounding maximum HTTP request and retry durations
        iso_stale_cutoff = (now - timedelta(seconds=300)).isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            # 1. Daily budget check (completed calls + active unexpired reservations)
            cursor.execute(
                """
                SELECT COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_24h, iso_stale_cutoff),
            )
            daily_used = cursor.fetchone()[0]
            if daily_used + credits > daily_budget:
                conn.rollback()
                return (
                    False,
                    f"Daily request budget reached ({daily_used}/{daily_budget}). Request blocked.",
                    None,
                )

            # 2. Rolling 15-minute budget check
            cursor.execute(
                """
                SELECT COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_15m, iso_stale_cutoff),
            )
            used_15m = cursor.fetchone()[0]
            if used_15m + credits > rolling_15m_budget:
                conn.rollback()
                return (
                    False,
                    f"Rolling 15-minute budget reached ({used_15m}/{rolling_15m_budget}). Please wait.",
                    None,
                )

            # 3. Minimum refresh interval for this profile
            if min_interval_seconds > 0:
                cursor.execute(
                    """
                    SELECT requested_at FROM provider_request_log
                    WHERE provider_id = ? AND profile = ?
                      AND outcome != 'canceled'
                    ORDER BY requested_at DESC LIMIT 1
                    """,
                    (provider_id, profile),
                )
                last_row = cursor.fetchone()
                if last_row and last_row[0]:
                    try:
                        last_time = datetime.fromisoformat(last_row[0])
                        if last_time.tzinfo is None:
                            last_time = last_time.replace(tzinfo=timezone.utc)
                        elapsed = (now - last_time).total_seconds()
                        if elapsed < min_interval_seconds:
                            conn.rollback()
                            return (
                                False,
                                f"Minimum interval between {profile} refreshes not elapsed ({elapsed:.1f}s < {min_interval_seconds:.0f}s).",
                                None,
                            )
                    except Exception:
                        pass

            # Atomically insert reservation row
            cursor.execute(
                """
                INSERT INTO provider_request_log (
                    provider_id, profile, requested_at, status_code, outcome, credits_consumed, latency_ms
                ) VALUES (?, ?, ?, NULL, 'reserved', ?, 0.0)
                """,
                (provider_id, profile, now.isoformat(), credits),
            )
            reservation_id = cursor.lastrowid
            conn.commit()
            return True, None, reservation_id

    def finalize_provider_request(
        self,
        reservation_id: int,
        status_code: Optional[int],
        outcome: str,
        latency_ms: float = 0.0,
        credits_consumed: Optional[int] = None,
    ) -> None:
        """Updates a reserved provider request with its final outcome and consumed credits.

        Conservative quota accounting:
        Ambiguous outcomes (timeouts, connection resets, 5xx) are conservatively billed as consumed
        (1 credit). Only demonstrably undispatched requests (outcome == 'canceled') are refunded with 0 credits.
        """
        if credits_consumed is None:
            if outcome == "canceled":
                actual_credits = 0
            else:
                actual_credits = 1
        else:
            actual_credits = credits_consumed

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE provider_request_log
                SET status_code = ?,
                    outcome = ?,
                    credits_consumed = ?,
                    latency_ms = ?
                WHERE id = ?
                """,
                (status_code, outcome, actual_credits, latency_ms, reservation_id),
            )
            conn.commit()

    def get_provider_quota_telemetry(
        self,
        provider_id: str = "newsdata_io",
        daily_budget: int = 50,
        rolling_15m_budget: int = 10,
    ) -> Dict[str, Any]:
        """Returns real-time usage metrics from the persistent request log."""
        now = datetime.now(timezone.utc)
        iso_24h = (now - timedelta(days=1)).isoformat()
        iso_15m = (now - timedelta(minutes=15)).isoformat()
        iso_stale_cutoff = (now - timedelta(seconds=300)).isoformat()

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_24h, iso_stale_cutoff),
            )
            d_row = cursor.fetchone()
            daily_requests = d_row[0] if d_row else 0
            daily_credits = d_row[1] if d_row else 0

            cursor.execute(
                """
                SELECT COALESCE(SUM(credits_consumed), 0)
                FROM provider_request_log
                WHERE provider_id = ? AND requested_at >= ?
                  AND (
                    (outcome NOT IN ('reserved', 'canceled') AND credits_consumed > 0)
                    OR (outcome = 'reserved' AND requested_at >= ?)
                  )
                """,
                (provider_id, iso_15m, iso_stale_cutoff),
            )
            r_15m = cursor.fetchone()
            used_15m = r_15m[0] if r_15m else 0

            cursor.execute(
                "SELECT requested_at, outcome FROM provider_request_log WHERE provider_id = ? ORDER BY requested_at DESC LIMIT 1",
                (provider_id,),
            )
            last_req = cursor.fetchone()

        return {
            "provider_id": provider_id,
            "daily_requests_used": daily_requests,
            "daily_requests_budget": daily_budget,
            "daily_credits_estimated": daily_credits,
            "rolling_15m_used": used_15m,
            "rolling_15m_budget": rolling_15m_budget,
            "is_exhausted": (daily_requests >= daily_budget) or (used_15m >= rolling_15m_budget),
            "last_request_at": last_req[0] if last_req else None,
            "last_outcome": last_req[1] if last_req else None,
        }
