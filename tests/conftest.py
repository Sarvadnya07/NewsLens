"""Global pytest configuration and test environment isolation for NewsLens India.

Guarantees:
- Strict test isolation: tests run against an ephemeral SQLite database in tempdir.
- Data safety: tests NEVER connect to or mutate data/newslens.db or data/newslens.db.backup.
- Clean session seeding: supplies deterministic articles and source health for UI and API tests.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest

from backend.api.dependencies import get_news_service
from src.models import NormalizedArticle
from src.storage.database import DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_DB_PATH = (PROJECT_ROOT / "data" / "newslens.db").resolve()
BACKUP_DB_PATH = (PROJECT_ROOT / "data" / "newslens.db.backup").resolve()


@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path: Path) -> Generator[str, None, None]:
    """Function-scoped fixture ensuring complete test isolation with a dedicated seeded database per test."""
    temp_db_path = str((tmp_path / "isolated_test_newslens.db").resolve())

    # Pre-test safety guard
    assert Path(temp_db_path).resolve() != REAL_DB_PATH, "Test DB resolves to real data/newslens.db"
    assert Path(temp_db_path).resolve() != BACKUP_DB_PATH, (
        "Test DB resolves to real data/newslens.db.backup"
    )

    # Set environment variable before any service or test client initializes
    old_env_path = os.environ.get("NEWSLENS_DB_PATH")
    os.environ["NEWSLENS_DB_PATH"] = temp_db_path

    # Clear FastAPI service dependency cache
    try:
        get_news_service.cache_clear()
    except Exception:
        pass

    # Initialize schema and migrations on the test database
    db = DatabaseManager(db_path=temp_db_path)

    # Seed deterministic test articles for UI and contract validation
    now_iso = datetime.now(timezone.utc).isoformat()
    seed_articles = []

    # 18 articles from The Hindu (RSS)
    for i in range(1, 19):
        seed_articles.append(
            NormalizedArticle(
                id=f"rss_hindu_{i:03d}",
                title=f"The Hindu Report {i}: National policy developments and infrastructure updates",
                url=f"https://www.thehindu.com/news/national/article_{i:03d}.html",
                publisher="The Hindu",
                published_at=now_iso,
                ingested_at=now_iso,
                source_type="rss",
                summary=f"Detailed report {i} regarding governance, railways and budgetary allocations.",
                language="en",
                country="IN",
                query="",
                origin="rss",
            )
        )

    # 12 articles from NDTV (RSS)
    for i in range(1, 13):
        seed_articles.append(
            NormalizedArticle(
                id=f"rss_ndtv_{i:03d}",
                title=f"NDTV Special {i}: India economic outlook and parliamentary discussions",
                url=f"https://www.ndtv.com/india-news/article_{i:03d}.html",
                publisher="NDTV",
                published_at=now_iso,
                ingested_at=now_iso,
                source_type="rss",
                summary=f"Analysis {i} covering election reforms, state development and trade.",
                language="en",
                country="IN",
                query="",
                origin="rss",
            )
        )

    # 2 manual user submissions
    seed_articles.append(
        NormalizedArticle(
            id="manual_test_001",
            title="Fact check investigation on viral social media claims regarding currency demonetization",
            url="manual://test_submission_001",
            publisher="Manual User Submission",
            published_at=now_iso,
            ingested_at=now_iso,
            source_type="manual",
            summary="User submitted text for misinformation analysis and BM25 cross-reference.",
            language="en",
            country="IN",
            query="manual",
            origin="manual",
        )
    )
    seed_articles.append(
        NormalizedArticle(
            id="manual_test_002",
            title="Circulated notice regarding university exam cancellation and fee refund",
            url="manual://test_submission_002",
            publisher="Manual User Submission",
            published_at=now_iso,
            ingested_at=now_iso,
            source_type="manual",
            summary="User provided text for verification against PIB and press bureau releases.",
            language="en",
            country="IN",
            query="manual",
            origin="manual",
        )
    )

    db.upsert_articles(seed_articles)

    # Seed source health statuses
    rss_feeds = [
        "The Times of India (National)",
        "The Hindu (National)",
        "NDTV (India News)",
        "Indian Express (India)",
        "Hindustan Times (India)",
        "Livemint (National & Economy)",
    ]
    for feed in rss_feeds:
        db.record_source_status(
            source_name=feed,
            source_type="rss",
            status="success",
            items_fetched=25,
            http_status=200,
            latency_ms=120.5,
            is_active=1,
        )

    db.record_source_status(
        source_name="GDELT 2.0 Doc API",
        source_type="gdelt",
        status="success",
        items_fetched=20,
        http_status=200,
        latency_ms=350.0,
        is_active=1,
    )

    db.record_source_status(
        source_name="Deccan Herald (National)",
        source_type="rss",
        status="provider_unavailable",
        items_fetched=0,
        http_status=404,
        latency_ms=450.0,
        error_message="Retired upstream RSS endpoint",
        is_active=0,
    )

    yield temp_db_path

    # Teardown
    try:
        get_news_service.cache_clear()
    except Exception:
        pass

    if old_env_path is not None:
        os.environ["NEWSLENS_DB_PATH"] = old_env_path
    else:
        os.environ.pop("NEWSLENS_DB_PATH", None)
