"""Phase 2 comprehensive regression tests for backend, external APIs, ingestion, and database."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.ingestion.gdelt import GdeltClient
from src.ingestion.models import (
    STATUS_INVALID_RESPONSE,
    STATUS_NO_RESULTS,
    STATUS_PROVIDER_UNAVAILABLE,
    STATUS_RATE_LIMITED,
    STATUS_SUCCESS,
    STATUS_TIMEOUT,
    ProviderFetchResult,
)
from src.ingestion.rss import RssIngestionService
from src.models import NormalizedArticle
from src.services.news_service import NewsLensService
from src.storage.database import DatabaseManager

# ---------------------------------------------------------------------------
# 1. GDELT Integration Tests
# ---------------------------------------------------------------------------


def test_gdelt_success():
    client = GdeltClient(min_interval_seconds=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {
        "articles": [
            {
                "url": "https://thehindu.com/sci-tech/isro-mission?utm_source=twitter",
                "title": "ISRO Satellite Launch Success",
                "domain": "thehindu.com",
                "seendate": "20261031T010000Z",
                "language": "English",
                "sourcecountry": "IN",
            }
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles("ISRO")
        assert res.status == STATUS_SUCCESS
        assert res.items_count == 1
        assert len(res.articles) == 1
        art = res.articles[0]
        assert art.source_type == "gdelt"
        assert "utm_source" not in art.url
        assert art.id.startswith("gdelt_")


def test_gdelt_empty_result():
    client = GdeltClient(min_interval_seconds=0.0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"articles": []}

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles("rare_nonexistent_query_string")
        assert res.status == STATUS_NO_RESULTS
        assert res.items_count == 0
        assert res.articles == []


def test_gdelt_429_rate_limit():
    client = GdeltClient(min_interval_seconds=0.0, max_retries=0)
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Please limit your request rate."

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles("test_query")
        assert res.status == STATUS_RATE_LIMITED
        assert res.items_count == 0
        assert "429" in (res.error_message or "")


def test_gdelt_timeout():
    client = GdeltClient(min_interval_seconds=0.0, max_retries=1, retry_delay_seconds=0.01)

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        res = client.fetch_articles("test_query")
        assert res.status == STATUS_TIMEOUT
        assert res.items_count == 0
        assert "timed out" in (res.error_message or "").lower()


def test_gdelt_invalid_payload():
    client = GdeltClient(min_interval_seconds=0.0, max_retries=0)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "text/html"}
    mock_resp.text = "<html><body>500 Internal Error</body></html>"
    mock_resp.json.side_effect = ValueError("No JSON object could be decoded")

    with patch("requests.get", return_value=mock_resp):
        res = client.fetch_articles("test_query")
        assert res.status == STATUS_INVALID_RESPONSE
        assert res.items_count == 0


# ---------------------------------------------------------------------------
# 2. RSS Ingestion Tests
# ---------------------------------------------------------------------------


def test_rss_success(tmp_path):
    service = RssIngestionService()
    valid_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Express</title>
            <link>https://express.in</link>
            <item>
                <title>Cabinet Approves Green Energy Corridor</title>
                <link>https://express.in/green-energy?ref=rss</link>
                <description>Union Cabinet chaired by Prime Minister approved phase two...</description>
                <pubDate>Fri, 30 Oct 2026 09:30:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://express.in/rss.xml"
    mock_resp.iter_content.return_value = [valid_xml]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.Session.get", return_value=mock_resp):
        res = service.fetch_feed_result("Test Express", "https://express.in/rss.xml")
        assert res.status == STATUS_SUCCESS
        assert res.items_count == 1
        assert len(res.articles) == 1
        art = res.articles[0]
        assert art.title == "Cabinet Approves Green Energy Corridor"
        assert "ref=rss" not in art.url


def test_rss_empty_feed():
    service = RssIngestionService()
    empty_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel><title>Empty</title></channel></rss>
    """
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://example.com/rss.xml"
    mock_resp.iter_content.return_value = [empty_xml]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.Session.get", return_value=mock_resp):
        res = service.fetch_feed_result("Empty Feed", "https://example.com/rss.xml")
        assert res.status == STATUS_NO_RESULTS
        assert res.items_count == 0


def test_rss_malformed_feed():
    service = RssIngestionService()
    malformed_xml = b"<<<not_xml>>>This is plain junk text."
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://example.com/bad.xml"
    mock_resp.iter_content.return_value = [malformed_xml]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.Session.get", return_value=mock_resp):
        res = service.fetch_feed_result("Broken Feed", "https://example.com/bad.xml")
        assert res.status in (STATUS_INVALID_RESPONSE, STATUS_NO_RESULTS)
        assert res.items_count == 0


def test_rss_oversized_feed():
    service = RssIngestionService(max_bytes=100)  # 100 bytes cap for testing
    huge_data = b"X" * 500
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://example.com/huge.xml"
    mock_resp.iter_content.return_value = [huge_data]
    mock_resp.__enter__.return_value = mock_resp

    with patch("requests.Session.get", return_value=mock_resp):
        res = service.fetch_feed_result("Oversized Feed", "https://example.com/huge.xml")
        assert res.status == STATUS_INVALID_RESPONSE
        assert "maximum response size" in (res.error_message or "").lower()


def test_rss_timeout():
    service = RssIngestionService()
    with patch("requests.Session.get", side_effect=requests.exceptions.Timeout("Timeout")):
        res = service.fetch_feed_result("Slow Feed", "https://slow.com/rss")
        assert res.status == STATUS_TIMEOUT
        assert res.items_count == 0


def test_rss_redirect_restrictions():
    service = RssIngestionService()
    # Direct loopback attempt
    res = service.fetch_feed_result("Loopback", "http://127.0.0.1:8080/feed")
    assert res.status == STATUS_INVALID_RESPONSE

    # Disallowed scheme
    res2 = service.fetch_feed_result("FTP Feed", "ftp://example.com/feed.xml")
    assert res2.status == STATUS_INVALID_RESPONSE


def test_partial_and_all_providers_failing():
    feeds = {
        "Good Feed": "https://good.com/rss",
        "Bad Feed": "https://bad.com/rss",
    }
    service = RssIngestionService(feeds=feeds)

    def mock_fetch(name, url):
        if "Good" in name:
            art = NormalizedArticle(
                id="rss_test1",
                title="Good Headline",
                url="https://good.com/1",
                publisher=name,
                published_at="2026-10-31T01:00:00Z",
                ingested_at="2026-10-31T01:00:00Z",
                source_type="rss",
            )
            return ProviderFetchResult(
                source_id="good",
                source_name=name,
                source_type="rss",
                status=STATUS_SUCCESS,
                articles=[art],
            )
        return ProviderFetchResult(
            source_id="bad",
            source_name=name,
            source_type="rss",
            status=STATUS_PROVIDER_UNAVAILABLE,
            articles=[],
        )

    with patch.object(service, "fetch_feed_result", side_effect=mock_fetch):
        res = service.fetch_all()
        assert res["total_count"] == 1
        assert res["stats"]["Good Feed"]["status"] == STATUS_SUCCESS
        assert res["stats"]["Bad Feed"]["status"] == STATUS_PROVIDER_UNAVAILABLE


# ---------------------------------------------------------------------------
# 3. Database Persistence, Idempotency & Search Tests
# ---------------------------------------------------------------------------


def test_database_idempotent_upsert(tmp_path):
    db_file = tmp_path / "test_db.db"
    db = DatabaseManager(str(db_file))

    art = NormalizedArticle(
        id="rss_unique_123",
        title="Original Title",
        url="https://example.in/post1",
        publisher="Example News",
        published_at="2026-10-30T10:00:00Z",
        ingested_at="2026-10-30T10:00:00Z",
        source_type="rss",
        summary="Short summary.",
    )

    # First insert returns True (newly inserted)
    is_new = db.upsert_article(art)
    assert is_new is True
    assert db.get_article_count() == 1

    # Second insert with updated title returns False (updated, not new)
    art.title = "Updated Title with Fresh Correction"
    is_new_again = db.upsert_article(art)
    assert is_new_again is False
    assert db.get_article_count() == 1

    fetched = db.get_articles(limit=10)
    assert len(fetched) == 1
    assert fetched[0].title == "Updated Title with Fresh Correction"


def test_database_literal_wildcard_search(tmp_path):
    db_file = tmp_path / "test_db.db"
    db = DatabaseManager(str(db_file))

    art1 = NormalizedArticle(
        id="art_1",
        title="Railways announces 100% discount for seniors",
        url="https://example.in/1",
        publisher="News",
        published_at="",
        ingested_at="2026-10-31T01:00:00Z",
        source_type="rss",
    )
    art2 = NormalizedArticle(
        id="art_2",
        title="Railways announces 100_percent discount for seniors",
        url="https://example.in/2",
        publisher="News",
        published_at="",
        ingested_at="2026-10-31T01:00:00Z",
        source_type="rss",
    )
    art3 = NormalizedArticle(
        id="art_3",
        title="Normal fare updates without symbols",
        url="https://example.in/3",
        publisher="News",
        published_at="",
        ingested_at="2026-10-31T01:00:00Z",
        source_type="rss",
    )
    db.upsert_articles([art1, art2, art3])

    # Search literal "%" should only match art1
    pct_matches = db.get_articles(query="100%")
    assert len(pct_matches) == 1
    assert pct_matches[0].id == "art_1"

    # Search literal "_" should only match art2
    underscore_matches = db.get_articles(query="100_")
    assert len(underscore_matches) == 1
    assert underscore_matches[0].id == "art_2"


def test_database_pagination_and_sorting(tmp_path):
    db_file = tmp_path / "test_db.db"
    db = DatabaseManager(str(db_file))

    articles = [
        NormalizedArticle(
            id=f"art_{i:02d}",
            title=f"Headline #{i:02d}",
            url=f"https://example.in/{i}",
            publisher="Press",
            published_at="",
            ingested_at=f"2026-10-31T01:{i:02d}:00Z",
            source_type="rss",
        )
        for i in range(15)
    ]
    db.upsert_articles(articles)
    assert db.get_article_count() == 15

    # Page 1: limit 5, offset 0 (descending)
    p1 = db.get_articles(limit=5, offset=0, order_by="ingested_at", ascending=False)
    assert len(p1) == 5
    assert p1[0].id == "art_14"

    # Page 2: limit 5, offset 5
    p2 = db.get_articles(limit=5, offset=5, order_by="ingested_at", ascending=False)
    assert len(p2) == 5
    assert p2[0].id == "art_09"

    # Total matching count
    assert db.count_matching_articles() == 15


def test_database_transaction_rollback_on_failure(tmp_path):
    db_file = tmp_path / "test_db.db"
    db = DatabaseManager(str(db_file))

    # Test that failed SQL transaction rolls back cleanly
    with pytest.raises(Exception):
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO articles (id, title, url, publisher, ingested_at, source_type) VALUES (?, ?, ?, ?, ?, ?)",
                ("rollback_1", "Will be rolled back", "http://test", "Pub", "now", "rss"),
            )
            # Deliberately cause a syntax error
            cursor.execute("INSERT INTO non_existent_table VALUES (1)")
            conn.commit()

    # Verify rollback
    assert db.get_article_count() == 0


def test_news_monitor_service_contract(tmp_path):
    db_file = tmp_path / "test_db.db"
    service = NewsLensService(db_path=str(db_file))

    for i in range(25):
        stype = "rss" if i % 2 == 0 else "gdelt"
        service.db.upsert_article(
            NormalizedArticle(
                id=f"mon_{i}",
                title=f"Ecosystem update {i} ISRO",
                url=f"https://domain{i}.in/art",
                publisher="Ecosystem Wire",
                published_at="",
                ingested_at=f"2026-10-31T02:{i:02d}:00Z",
                source_type=stype,
            )
        )

    res_all = service.query_monitor_articles(query="ISRO", limit=10)
    assert res_all["total_matching"] == 25
    assert len(res_all["articles"]) == 10
    assert res_all["page"] == 1

    res_rss = service.query_monitor_articles(source_type="rss", limit=50)
    assert res_rss["total_matching"] == 13
    assert len(res_rss["articles"]) == 13
