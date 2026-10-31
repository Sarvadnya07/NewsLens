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
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

from src.ingestion.models import VALID_PROVIDER_STATUSES
from src.models import NormalizedArticle, normalize_published_at

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
                    raw_metadata TEXT
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
                    error_message TEXT
                )
            """)
            conn.commit()

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

                    cursor.execute(
                        """
                        INSERT INTO articles (
                            id, title, url, publisher, published_at, ingested_at,
                            source_type, summary, language, country, query, raw_metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET
                            title=excluded.title,
                            url=excluded.url,
                            publisher=excluded.publisher,
                            published_at=excluded.published_at,
                            summary=excluded.summary,
                            query=excluded.query,
                            raw_metadata=excluded.raw_metadata
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
                        cursor.execute(
                            """
                            INSERT INTO articles (
                                id, title, url, publisher, published_at, ingested_at,
                                source_type, summary, language, country, query, raw_metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                title=excluded.title,
                                url=excluded.url,
                                publisher=excluded.publisher,
                                published_at=excluded.published_at,
                                summary=excluded.summary,
                                query=excluded.query,
                                raw_metadata=excluded.raw_metadata
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
    ) -> tuple[str, List[Any]]:
        """Builds the shared WHERE clause used by listing and counting queries."""
        clause = ""
        params: List[Any] = []

        if source_type:
            clause += " AND source_type = ?"
            params.append(source_type)

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
    ) -> List[NormalizedArticle]:
        """Retrieves articles with parameterized filtering, safe LIKE wildcards, and pagination."""
        with self._connect() as conn:
            cursor = conn.cursor()
            clause, params = self._build_filters(query, source_type, publisher, since_iso)
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
                    )
                )
            return result

    def count_matching_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        publisher: Optional[str] = None,
        since_iso: Optional[str] = None,
    ) -> int:
        """Total matching records, independent of the page size in use."""
        with self._connect() as conn:
            cursor = conn.cursor()
            clause, params = self._build_filters(query, source_type, publisher, since_iso)
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

    def record_source_status(
        self,
        source_name: str,
        source_type: str,
        status: str,
        items_fetched: int = 0,
        error_message: Optional[str] = None,
    ) -> None:
        """Records or updates the last known outcome for a source using standardized taxonomy."""
        now = datetime.now(timezone.utc).isoformat()
        clean_status = status if status in VALID_PROVIDER_STATUSES else "provider_unavailable"

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO source_status (
                    source_name, source_type, last_refresh_at, status, items_fetched, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name) DO UPDATE SET
                    source_type=excluded.source_type,
                    last_refresh_at=excluded.last_refresh_at,
                    status=excluded.status,
                    items_fetched=excluded.items_fetched,
                    error_message=excluded.error_message
                """,
                (
                    source_name,
                    source_type,
                    now,
                    clean_status,
                    items_fetched,
                    error_message,
                ),
            )
            conn.commit()

    def get_all_source_status(self) -> List[Dict[str, Any]]:
        """Returns all recorded source statuses ordered by most recent refresh."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM source_status ORDER BY last_refresh_at DESC")
            return [dict(r) for r in cursor.fetchall()]
