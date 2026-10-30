"""SQLite database persistence for NewsLens India."""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from src.models import NormalizedArticle


class DatabaseManager:
    """Thread-safe SQLite manager for normalized news articles and cached feeds."""

    def __init__(self, db_path: str = "data/newslens.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
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
        """Inserts or updates a normalized article. Returns True if inserted new."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            raw_meta_json = json.dumps(article.raw_metadata or {})
            cursor.execute("""
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
            """, (
                article.id,
                article.title,
                article.url,
                article.publisher,
                article.published_at,
                article.ingested_at,
                article.source_type,
                article.summary,
                article.language,
                article.country,
                article.query,
                raw_meta_json
            ))
            conn.commit()
            return cursor.rowcount > 0

    def upsert_articles(self, articles: List[NormalizedArticle]) -> int:
        """Batch upserts normalized articles."""
        if not articles:
            return 0
        count = 0
        for art in articles:
            if self.upsert_article(art):
                count += 1
        return count

    def get_articles(
        self,
        query: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[NormalizedArticle]:
        """Retrieves articles with optional filtering and pagination."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM articles WHERE 1=1"
            params: List[Any] = []

            if source_type:
                sql += " AND source_type = ?"
                params.append(source_type)

            if query:
                sql += " AND (title LIKE ? OR summary LIKE ? OR query LIKE ?)"
                wildcard = f"%{query}%"
                params.extend([wildcard, wildcard, wildcard])

            sql += " ORDER BY published_at DESC, ingested_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            result = []
            for r in rows:
                raw_meta = {}
                if r["raw_metadata"]:
                    try:
                        raw_meta = json.loads(r["raw_metadata"])
                    except Exception:
                        pass
                result.append(NormalizedArticle(
                    id=r["id"],
                    title=r["title"],
                    url=r["url"],
                    publisher=r["publisher"],
                    published_at=r["published_at"],
                    ingested_at=r["ingested_at"],
                    source_type=r["source_type"],
                    summary=r["summary"],
                    language=r["language"],
                    country=r["country"],
                    query=r["query"],
                    raw_metadata=raw_meta
                ))
            return result

    def get_article_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            return cursor.fetchone()[0]

    def record_source_status(
        self,
        source_name: str,
        source_type: str,
        status: str,
        items_fetched: int = 0,
        error_message: Optional[str] = None
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO source_status (
                    source_name, source_type, last_refresh_at, status, items_fetched, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_name) DO UPDATE SET
                    source_type=excluded.source_type,
                    last_refresh_at=excluded.last_refresh_at,
                    status=excluded.status,
                    items_fetched=excluded.items_fetched,
                    error_message=excluded.error_message
            """, (source_name, source_type, now, status, items_fetched, error_message))
            conn.commit()

    def get_all_source_status(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM source_status ORDER BY last_refresh_at DESC")
            return [dict(r) for r in cursor.fetchall()]
