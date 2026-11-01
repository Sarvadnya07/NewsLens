"""Comprehensive unit and integration tests for the Bounded Top 10 News Experience.

Tests:
1. Zero results returns empty list [].
2. Exactly 1 result returns 1 item with metadata.
3. Exactly 10 results returns 10 items.
4. >10 eligible candidates returns strictly at most 10 items.
5. Thematic deduplication prevents duplicates from consuming multiple slots.
6. Publisher diversity capping prevents a single publisher from dominating.
7. Image URL metadata correctly propagates through NewsLensService and FastAPI /dashboard/summary.
8. API contracts return top_stories_limit: 10 and top_stories_count: len(recent_articles).
"""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient

from backend.main import app
from src.models import NormalizedArticle
from src.services.news_service import NewsLensService
from src.storage.database import DatabaseManager


def create_article(
    db: DatabaseManager,
    article_id: str,
    title: str,
    publisher: str,
    url: str,
    published_at: datetime.datetime,
    source_type: str = "rss",
    image_url: str | None = None,
) -> NormalizedArticle:
    metadata = {}
    if image_url:
        metadata["image_url"] = image_url

    art = NormalizedArticle(
        id=article_id,
        title=title,
        url=url,
        publisher=publisher,
        source_type=source_type,
        published_at=published_at.isoformat(),
        ingested_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        language="en",
        country="IN",
        raw_metadata=metadata,
        summary=f"Summary for {title}",
    )
    db.upsert_articles([art])
    return art


def test_top_stories_zero_results(tmp_path):
    temp_db_path = str(tmp_path / "zero_stories.db")
    DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    results = service.get_top_dashboard_stories(limit=10)
    assert results == []


def test_top_stories_one_result(tmp_path):
    temp_db_path = str(tmp_path / "one_story.db")
    db = DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    create_article(
        db,
        article_id="art_1",
        title="Sole Article in Observatory",
        publisher="The Hindu",
        url="https://thehindu.com/sole",
        published_at=datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.timezone.utc),
        image_url="https://images.thehindu.com/sole.jpg",
    )

    results = service.get_top_dashboard_stories(limit=10)
    assert len(results) == 1
    assert results[0].id == "art_1"
    assert results[0].raw_metadata.get("image_url") == "https://images.thehindu.com/sole.jpg"


def test_top_stories_exactly_ten(tmp_path):
    temp_db_path = str(tmp_path / "ten_stories.db")
    db = DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    base_time = datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.timezone.utc)
    distinct_topics = [
        "Monsoon alert declared across coastal Gujarat regions",
        "Reserve Bank of India maintains benchmark repo rate steady",
        "ISRO prepares launch vehicle for upcoming lunar rover mission",
        "Parliament passes new renewable energy transmission legislation",
        "Automotive sales show double-digit expansion in third quarter",
        "Supreme Court constitution bench hears fundamental rights petition",
        "High-speed railway corridor completes major tunneling phase",
        "Semiconductor manufacturing fabrication unit inaugurated in Dholera",
        "National digital health mission registers milestone verifications",
        "Agricultural exports touch record high amid steady global demand",
    ]
    for i, topic in enumerate(distinct_topics):
        create_article(
            db,
            article_id=f"art_{i}",
            title=topic,
            publisher=f"Publisher_{i % 5}",
            url=f"https://example.com/distinct-{i}",
            published_at=base_time - datetime.timedelta(minutes=i * 10),
        )

    results = service.get_top_dashboard_stories(limit=10)
    assert len(results) == 10
    # Must be recency ordered
    for idx in range(len(results) - 1):
        assert results[idx].published_at >= results[idx + 1].published_at


def test_top_stories_bounds_exceeding_pool_to_ten(tmp_path):
    temp_db_path = str(tmp_path / "exceed_stories.db")
    db = DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    base_time = datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.timezone.utc)
    topics = [
        "Monsoon alert declared across coastal Gujarat regions",
        "Reserve Bank of India maintains benchmark repo rate steady",
        "ISRO prepares launch vehicle for upcoming lunar rover mission",
        "Parliament passes new renewable energy transmission legislation",
        "Automotive sales show double-digit expansion in third quarter",
        "Supreme Court constitution bench hears fundamental rights petition",
        "High-speed railway corridor completes major tunneling phase",
        "Semiconductor manufacturing fabrication unit inaugurated in Dholera",
        "National digital health mission registers milestone verifications",
        "Agricultural exports touch record high amid steady global demand",
        "Global crude oil prices fluctuate following geopolitical summits",
        "Defense research agency successfully tests hypersonic glide system",
        "Urban metro network extends passenger operations across suburbs",
        "Port logistics authorities implement paperless customs corridor",
        "Aviation ministry issues revised airworthiness safety protocols",
        "State universities introduce integrated artificial intelligence curriculum",
        "Telecom operators deploy localized 6G experimental testbeds",
        "Pharmaceutical research laboratory clears international audit review",
        "National highway expansion reaches ninety percent completion mark",
        "Heavy industries ministry rolls out industrial subsidy framework",
    ]
    # Insert 20 distinct articles across various publishers
    for i, topic in enumerate(topics):
        create_article(
            db,
            article_id=f"art_exceed_{i}",
            title=topic,
            publisher=f"Publisher_{i % 6}",
            url=f"https://example.com/exceed-{i}",
            published_at=base_time - datetime.timedelta(minutes=i * 5),
        )

    results = service.get_top_dashboard_stories(limit=10)
    assert len(results) == 10  # Strictly bounded to 10


def test_top_stories_deduplication_clusters_thematic_duplicates(tmp_path):
    temp_db_path = str(tmp_path / "dedup_stories.db")
    db = DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    base_time = datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.timezone.utc)

    # 3 duplicate articles on the exact same event
    create_article(
        db,
        article_id="dup_1",
        title="NDRF deploys rescue teams in coastal Gujarat amid cyclonic alert",
        publisher="PTI",
        url="https://pti.in/story1",
        published_at=base_time,
    )
    create_article(
        db,
        article_id="dup_2",
        title="NDRF deploys rescue teams in coastal Gujarat amid cyclonic alert",
        publisher="ANI",
        url="https://ani.in/story2",
        published_at=base_time - datetime.timedelta(minutes=1),
    )
    create_article(
        db,
        article_id="dup_3",
        title="Gujarat cyclone: NDRF deploys rescue teams in coastal Gujarat amid cyclonic alert",
        publisher="The Hindu",
        url="https://thehindu.com/story3",
        published_at=base_time - datetime.timedelta(minutes=2),
    )

    # 1 distinct article
    create_article(
        db,
        article_id="distinct_1",
        title="ISRO successfully conducts high-thrust cryogenic engine qualification test",
        publisher="ISRO Press",
        url="https://isro.gov.in/test",
        published_at=base_time - datetime.timedelta(minutes=5),
    )

    results = service.get_top_dashboard_stories(limit=10)

    # The 3 duplicate stories should not occupy 3 slots
    titles = [r.title for r in results]
    ndrf_matches = [t for t in titles if "NDRF deploys" in t]
    assert len(ndrf_matches) == 1
    assert any("ISRO" in t for t in titles)


def test_top_stories_publisher_diversity_cap(tmp_path):
    temp_db_path = str(tmp_path / "diversity_stories.db")
    db = DatabaseManager(temp_db_path)
    service = NewsLensService(db_path=temp_db_path)

    base_time = datetime.datetime(2026, 11, 2, 10, 0, tzinfo=datetime.timezone.utc)

    # Insert 8 articles from dominant publisher "SingleWire"
    for i in range(8):
        create_article(
            db,
            article_id=f"wire_{i}",
            title=f"Diverse Subject Matter Report {i} from Wire",
            publisher="SingleWire",
            url=f"https://singlewire.com/{i}",
            published_at=base_time - datetime.timedelta(minutes=i),
        )

    # Insert 4 articles from other publishers
    for i in range(4):
        create_article(
            db,
            article_id=f"other_{i}",
            title=f"Distinct Other Topic Heading {i} Local Gazette",
            publisher=f"OtherPublisher_{i}",
            url=f"https://otherpub.com/{i}",
            published_at=base_time - datetime.timedelta(minutes=10 + i),
        )

    results = service.get_top_dashboard_stories(limit=10)

    # SingleWire should be capped at max_per_publisher (max(2, 10//3) == 3)
    singlewire_count = sum(1 for r in results if r.publisher == "SingleWire")
    assert singlewire_count <= 3
    assert len(results) <= 10


def test_dashboard_api_returns_bounded_top_stories_and_metadata(isolated_test_db):
    # isolated_test_db fixture seeds 32 articles in conftest
    with TestClient(app) as client:
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200
        json_resp = resp.json()
        assert json_resp["success"] is True
        data = json_resp["data"]

        # Telemetry & contract fields
        assert data["top_stories_limit"] == 10
        assert data["top_stories_count"] <= 10
        assert len(data["recent_articles"]) <= 10
        assert len(data["recent_articles"]) == data["top_stories_count"]

        # Ensure every article has image_url key (can be null or string)
        for art in data["recent_articles"]:
            assert "image_url" in art
