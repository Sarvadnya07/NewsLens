"""Comprehensive test suite for NewsLens India.

Covers:
- Text preprocessing & cleaning
- ML model loading, inference, empty/invalid input handling
- GDELT normalization & error resilience
- RSS parsing & malformed feed handling
- BM25 fact check retrieval & no-match behavior
- Deduplication & cosine clustering
- SQLite persistence & parameterization
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from src.models import NormalizedArticle, FactCheckRecord
from src.preprocessing.cleaner import clean_text, tokenize_text
from src.storage.database import DatabaseManager
from src.ingestion.gdelt import GdeltClient
from src.ingestion.rss import RssIngestionService
from src.ml.predict import FakeNewsScreeningModel
from src.retrieval.fact_check import FactCheckRetriever
from src.processing.deduplication import NewsDeduplicator
from src.services.news_service import NewsLensService


# 1. Text Preprocessing Tests
def test_clean_text_basic():
    raw = "<p>Check out https://example.com for <b>BREAKING</b> news!!!</p>"
    cleaned = clean_text(raw)
    assert "breaking" in cleaned
    assert "<p>" not in cleaned
    assert "https" not in cleaned
    assert "!" not in cleaned


def test_clean_text_empty_and_none():
    assert clean_text("") == ""
    assert clean_text(None) == ""
    assert clean_text("   ") == ""


def test_tokenize_text():
    tokens = tokenize_text("The government launched the digital policy in New Delhi.")
    assert "government" in tokens
    assert "policy" in tokens
    # Stopword 'the' should be filtered
    assert "the" not in tokens


# 2. ML Inference & Artifact Tests
def test_ml_model_loading_and_inference():
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    # Test sample statement
    res = model.predict("Government announces new budget allocation for infrastructure.")
    assert res["status"] == "success"
    assert "label" in res
    assert 0.0 <= res["confidence"] <= 1.0
    assert 0.0 <= res["prob_fake"] <= 1.0
    assert 0.0 <= res["prob_true"] <= 1.0
    assert "uncertainty_note" in res


def test_ml_model_empty_and_short_input():
    model = FakeNewsScreeningModel()
    res_empty = model.predict("")
    assert res_empty["status"] == "empty_input"
    assert res_empty["confidence"] == 0.0

    res_short = model.predict("Hi")
    assert res_short["status"] == "short_input"


# 3. GDELT Normalization & Error Resilience Tests
def test_gdelt_normalization_mocked():
    client = GdeltClient(min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {
        "articles": [
            {
                "url": "https://example.in/news/123",
                "title": "ISRO launches new communications satellite",
                "seendate": "20261030T100000Z",
                "domain": "example.in",
                "language": "English",
                "sourcecountry": "IN"
            }
        ]
    }

    with patch("requests.get", return_value=mock_resp):
        articles = client.search_articles("ISRO")
        assert len(articles) == 1
        art = articles[0]
        assert art.title == "ISRO launches new communications satellite"
        assert art.publisher == "example.in"
        assert art.source_type == "gdelt"
        assert art.country == "IN"


def test_gdelt_rate_limit_and_error_handling():
    client = GdeltClient(min_interval_seconds=0.0)

    # 429 Rate limited response
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Please limit requests"

    with patch("requests.get", return_value=mock_429):
        articles = client.search_articles("test")
        assert articles == []

    # Network exception
    with patch("requests.get", side_effect=Exception("Connection refused")):
        articles = client.search_articles("test")
        assert articles == []


# 4. RSS Ingestion & Malformed Feeds Tests
def test_rss_feed_parsing_mocked():
    service = RssIngestionService()

    mock_feed = MagicMock()
    mock_feed.status = 200
    entry1 = MagicMock()
    entry1.title = "Supreme court hears landmark petition"
    entry1.link = "https://thehindu.com/news/1"
    entry1.summary = "A bench headed by Chief Justice..."
    entry1.published = "Fri, 30 Oct 2026 10:00:00 GMT"

    mock_feed.entries = [entry1]

    with patch("feedparser.parse", return_value=mock_feed):
        articles = service.fetch_feed("The Hindu", "https://thehindu.com/feed.rss")
        assert len(articles) == 1
        assert articles[0].title == "Supreme court hears landmark petition"
        assert articles[0].publisher == "The Hindu"
        assert articles[0].source_type == "rss"


def test_rss_malformed_feed_handling():
    service = RssIngestionService()

    with patch("feedparser.parse", side_effect=Exception("XML Syntax Error")):
        articles = service.fetch_feed("Broken Feed", "https://invalid.com/rss")
        assert articles == []


# 5. BM25 Fact Check Retrieval Tests
def test_fact_check_retrieval_match(tmp_path):
    data_file = tmp_path / "fact_checks.json"
    data_file.write_text("""[
        {
            "claim_id": "test_001",
            "claim": "Free laptop distribution scheme announced for all students.",
            "verdict": "Fake",
            "claimant": "WhatsApp",
            "fact_checker": "PIB Fact Check",
            "review_date": "2026-01-01",
            "source_url": "https://pib.gov.in",
            "explanation": "No such scheme exists."
        }
    ]""", encoding="utf-8")

    retriever = FactCheckRetriever(data_path=str(data_file))
    results = retriever.retrieve("students free laptop scheme", top_k=2)
    assert len(results) == 1
    assert results[0]["claim_id"] == "test_001"
    assert results[0]["verdict"] == "Fake"


def test_fact_check_retrieval_no_match(tmp_path):
    data_file = tmp_path / "fact_checks.json"
    data_file.write_text("[]", encoding="utf-8")
    retriever = FactCheckRetriever(data_path=str(data_file))
    results = retriever.retrieve("unrelated random text query")
    assert results == []


# 6. Deduplication & Related News Tests
def test_deduplicator_clusters():
    dedup = NewsDeduplicator(similarity_threshold=0.4)
    a1 = NormalizedArticle(
        id="1", title="RBI maintains repo rate at 6.5 percent", url="http://1",
        publisher="TOI", published_at="", ingested_at="", source_type="rss"
    )
    a2 = NormalizedArticle(
        id="2", title="RBI keeps repo rate unchanged at 6.5 percent", url="http://2",
        publisher="The Hindu", published_at="", ingested_at="", source_type="rss"
    )
    a3 = NormalizedArticle(
        id="3", title="Indian cricket team wins test series against Australia", url="http://3",
        publisher="NDTV", published_at="", ingested_at="", source_type="rss"
    )

    clusters = dedup.find_related_and_duplicates([a1, a2, a3])
    assert len(clusters) == 2  # The two RBI articles should cluster together, cricket separate
    multi = [c for c in clusters if c["total_coverage_count"] > 1]
    assert len(multi) == 1
    assert len(multi[0]["publishers"]) == 2


# 7. SQLite Persistence & Transactions Tests
def test_sqlite_persistence(tmp_path):
    db_file = tmp_path / "test_newslens.db"
    db = DatabaseManager(db_path=str(db_file))

    art = NormalizedArticle(
        id="test_art_01",
        title="Test Headline",
        url="https://example.com/art1",
        publisher="Test Media",
        published_at="2026-10-30T10:00:00Z",
        ingested_at="2026-10-30T10:05:00Z",
        source_type="rss",
        summary="Test summary content"
    )

    assert db.upsert_article(art) is True
    assert db.get_article_count() == 1

    fetched = db.get_articles(query="Headline")
    assert len(fetched) == 1
    assert fetched[0].id == "test_art_01"
    assert fetched[0].publisher == "Test Media"
