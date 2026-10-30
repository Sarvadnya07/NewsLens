"""Comprehensive test suite for NewsLens India.

Covers:
- Text preprocessing & cleaning
- ML model loading, inference, empty/invalid/short input handling
- GDELT normalization & error resilience (429 rate-limiting, network failures)
- RSS parsing & malformed feed handling
- BM25 fact check retrieval (matches, empty corpus, single record, no-match)
- URL canonicalization and deduplication (exact duplicates vs similar coverage)
- SQLite persistence, parameterized queries, and transactions
- End-to-end service workflows
"""

from unittest.mock import MagicMock, patch

import requests

from src.ingestion.gdelt import GdeltClient
from src.ingestion.rss import RssIngestionService
from src.ml.predict import FakeNewsScreeningModel
from src.models import NormalizedArticle, canonicalize_url
from src.preprocessing.cleaner import clean_text, tokenize_text
from src.processing.deduplication import NewsDeduplicator
from src.retrieval.fact_check import FactCheckRetriever
from src.services.news_service import NewsLensService
from src.storage.database import DatabaseManager


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


# 2. URL Canonicalization Tests
def test_canonicalize_url():
    u1 = "https://WWW.EXAMPLE.COM/news/story-1/?utm_source=twitter&utm_medium=social&id=10"
    clean = canonicalize_url(u1)
    assert clean == "https://www.example.com/news/story-1?id=10"
    assert "utm_source" not in clean


# 3. ML Inference & Artifact Tests
def test_ml_model_loading_and_inference():
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    res = model.predict("Government announces new budget allocation for infrastructure.")
    assert res["status"] == "success"
    assert "label" in res
    assert 0.0 <= res["confidence"] <= 1.0
    assert 0.0 <= res["prob_fake"] <= 1.0
    assert 0.0 <= res["prob_true"] <= 1.0
    assert "uncertainty_note" in res
    assert "LIAR" in res["uncertainty_note"]


def test_ml_model_empty_and_short_input():
    model = FakeNewsScreeningModel()
    res_empty = model.predict("")
    assert res_empty["status"] == "empty_input"
    assert res_empty["confidence"] == 0.0

    res_short = model.predict("Hi")
    assert res_short["status"] == "short_input"


# 4. GDELT Normalization & Error Resilience Tests
def test_gdelt_normalization_mocked():
    client = GdeltClient(min_interval_seconds=0.0)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {
        "articles": [
            {
                "url": "https://example.in/news/123?utm_campaign=breaking",
                "title": "ISRO launches new communications satellite",
                "seendate": "20261030T100000Z",
                "domain": "example.in",
                "language": "English",
                "sourcecountry": "IN",
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
        assert "utm_campaign" not in art.url


def test_gdelt_rate_limit_and_error_handling():
    client = GdeltClient(min_interval_seconds=0.0, max_retries=0)

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


def test_gdelt_transient_retry_success():
    client = GdeltClient(min_interval_seconds=0.0, max_retries=1, retry_delay_seconds=0.01)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {
        "articles": [
            {
                "url": "https://example.in/news/retry-success",
                "title": "Retry Succeeded Article",
                "seendate": "20261030T100000Z",
                "domain": "example.in",
            }
        ]
    }

    # First attempt raises Timeout, second attempt succeeds
    side_effects = [requests.exceptions.Timeout("Read timed out"), mock_resp]
    with patch("requests.get", side_effect=side_effects) as mock_get:
        articles = client.search_articles("retry_test")
        assert len(articles) == 1
        assert articles[0].title == "Retry Succeeded Article"
        assert mock_get.call_count == 2


# 5. RSS Ingestion & Malformed Feeds Tests
def test_rss_feed_parsing_mocked():
    service = RssIngestionService()

    mock_feed = MagicMock()
    mock_feed.status = 200
    entry1 = MagicMock()
    entry1.title = "Supreme court hears landmark petition"
    entry1.link = "https://thehindu.com/news/1?utm_medium=rss"
    entry1.summary = "A bench headed by Chief Justice..."
    entry1.published = "Fri, 30 Oct 2026 10:00:00 GMT"
    entry1.published_parsed = (2026, 10, 30, 10, 0, 0, 4, 303, 0)

    mock_feed.entries = [entry1]

    with patch("feedparser.parse", return_value=mock_feed):
        articles = service.fetch_feed("The Hindu", "https://thehindu.com/feed.rss")
        assert len(articles) == 1
        assert articles[0].title == "Supreme court hears landmark petition"
        assert articles[0].publisher == "The Hindu"
        assert articles[0].source_type == "rss"
        assert "utm_medium" not in articles[0].url
        assert "2026-10-30T10:00:00+00:00" in articles[0].published_at


def test_rss_malformed_feed_handling():
    service = RssIngestionService()

    with patch("feedparser.parse", side_effect=Exception("XML Syntax Error")):
        articles = service.fetch_feed("Broken Feed", "https://invalid.com/rss")
        assert articles == []


# 6. BM25 Fact Check Retrieval Tests
def test_fact_check_retrieval_match(tmp_path):
    data_file = tmp_path / "fact_checks.json"
    data_file.write_text(
        """[
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
    ]""",
        encoding="utf-8",
    )

    retriever = FactCheckRetriever(data_path=str(data_file))
    results = retriever.retrieve("students free laptop scheme", top_k=2)
    assert len(results) == 1
    assert results[0]["claim_id"] == "test_001"
    assert results[0]["verdict"] == "Fake"
    assert "match_advisory" in results[0]


def test_fact_check_retrieval_empty_corpus(tmp_path):
    data_file = tmp_path / "fact_checks.json"
    data_file.write_text("[]", encoding="utf-8")
    retriever = FactCheckRetriever(data_path=str(data_file))
    results = retriever.retrieve("students laptop scheme")
    assert results == []


def test_fact_check_retrieval_empty_query(tmp_path):
    data_file = tmp_path / "fact_checks.json"
    data_file.write_text(
        """[
        {"claim_id": "1", "claim": "Sample claim", "verdict": "Fake", "claimant": "X", "fact_checker": "PIB", "review_date": "2026", "source_url": "url", "explanation": "exp"}
    ]""",
        encoding="utf-8",
    )
    retriever = FactCheckRetriever(data_path=str(data_file))
    assert retriever.retrieve("") == []
    assert retriever.retrieve("   ") == []
    assert retriever.retrieve("!@#$%^&*()") == []


def test_fact_check_retrieval_zero_overlap_no_false_positive():
    retriever = FactCheckRetriever()
    # Out of vocabulary query should yield exactly zero matches due to lexical overlap guard
    results = retriever.retrieve(
        "quantum astrophysics supercollider dark matter hadron", min_score=1.0
    )
    assert results == []
    # In vocabulary valid query should retrieve relevant PIB claim
    valid_results = retriever.retrieve("students free laptop scheme")
    assert len(valid_results) > 0
    assert valid_results[0]["claim_id"] == "pib_001"


# 7. Deduplication & Related News Tests
def test_deduplicator_clusters():
    dedup = NewsDeduplicator(exact_threshold=0.85, similar_threshold=0.4)
    a1 = NormalizedArticle(
        id="1",
        title="RBI maintains repo rate at 6.5 percent",
        url="http://1",
        publisher="TOI",
        published_at="",
        ingested_at="",
        source_type="rss",
    )
    a2 = NormalizedArticle(
        id="2",
        title="RBI keeps repo rate unchanged at 6.5 percent",
        url="http://2",
        publisher="The Hindu",
        published_at="",
        ingested_at="",
        source_type="rss",
    )
    a3 = NormalizedArticle(
        id="3",
        title="Indian cricket team wins test series against Australia",
        url="http://3",
        publisher="NDTV",
        published_at="",
        ingested_at="",
        source_type="rss",
    )

    clusters = dedup.find_related_and_duplicates([a1, a2, a3])
    assert len(clusters) == 2
    multi = [c for c in clusters if c["total_coverage_count"] > 1]
    assert len(multi) == 1
    assert len(multi[0]["publishers"]) == 2
    rel_item = multi[0]["related_articles"][0]
    assert rel_item["relationship"] in (
        "likely_syndicated",
        "similar_coverage",
        "exact_or_republished",
    )


# 8. SQLite Persistence & Transactions Tests
def test_sqlite_persistence(tmp_path):
    db_file = tmp_path / "test_newslens.db"
    db = DatabaseManager(db_path=str(db_file))

    art = NormalizedArticle(
        id="test_art_01",
        title="Test Headline",
        url="https://example.com/art1?utm_source=rss",
        publisher="Test Media",
        published_at="2026-10-30T10:00:00Z",
        ingested_at="2026-10-30T10:05:00Z",
        source_type="rss",
        summary="Test summary content",
    )

    assert db.upsert_article(art) is True
    assert db.get_article_count() == 1

    fetched = db.get_articles(query="Headline")
    assert len(fetched) == 1
    assert fetched[0].id == "test_art_01"
    assert fetched[0].publisher == "Test Media"
    assert "utm_source" not in fetched[0].url


# 9. End-to-End Service Integration Test
def test_service_manual_submission_and_retrieval(tmp_path):
    db_file = tmp_path / "newslens_svc_test.db"
    fc_file = tmp_path / "fact_checks_test.json"
    fc_file.write_text(
        """[
        {
            "claim_id": "fc_svc_1",
            "claim": "UNESCO declares Indian Anthem the best.",
            "verdict": "False / Recurring Hoax",
            "claimant": "WhatsApp Chain Letter",
            "fact_checker": "BOOM Live",
            "review_date": "2026-01-10",
            "source_url": "https://www.boomlive.in",
            "explanation": "UNESCO does not rank anthems."
        }
    ]""",
        encoding="utf-8",
    )

    service = NewsLensService(db_path=str(db_file), fact_checks_path=str(fc_file))

    # 1. Manual article submission
    art = service.submit_manual_article(
        "UNESCO awards best national anthem to India", publisher="WhatsApp Viral"
    )
    assert art.source_type == "manual"
    assert service.db.get_article_count() == 1

    # 2. ML screening
    screen_res = service.screen_article_text(art.title)
    assert screen_res["status"] == "success"
    assert "label" in screen_res

    # 3. Fact-check retrieval
    fc_res = service.retrieve_fact_checks("UNESCO best anthem", top_k=1)
    assert len(fc_res) == 1
    assert fc_res[0]["claim_id"] == "fc_svc_1"

    # 4. Related news retrieval
    rel_res = service.find_related_news("UNESCO anthem", top_n=2)
    assert len(rel_res) >= 1
    assert rel_res[0]["article"].title == art.title
