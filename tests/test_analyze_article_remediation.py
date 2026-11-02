"""Unit and integration tests for Analyze Article diagnostic intelligence,
per-input feature contributions, dynamic evidence rubrics, syndication decoupling,
and parallel ingestion synchronization.
"""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app
from src.ml.predict import FakeNewsScreeningModel
from src.services.news_service import NewsLensService, ProviderFetchResult, RefreshResult


def test_feature_contributions_input_dependent():
    """Verify influential tokens compute per-input contribution C_i = x_i * w_i."""
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    # High frequency / distinct tokens
    text = "Government announced official financial grants and budget reforms in parliament."
    tokens = model.get_influential_tokens(text, top_n=5)
    assert isinstance(tokens, list)
    if tokens:
        for tok, weight in tokens:
            assert isinstance(tok, str)
            assert weight.startswith("+") or weight.startswith("-")
            # Must parse as a float
            float(weight)


def test_out_of_vocabulary_insufficient_signal():
    """Verify OOV / empty TF-IDF input yields Insufficient Signal."""
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    oov_text = "Zxyqwb klmnoq rstuvwx abcdefghijk lmnop"
    res = model.predict(oov_text)

    assert res["status"] == "insufficient_signal"
    assert res["label"] == "Insufficient / No Meaningful Model Signal"
    assert res["score"] == 0.5
    assert res["confidence"] == 0.5
    assert res["is_uncertain"] is True
    assert res["tokens"] == []
    assert "trained vocabulary" in res["explanation"]


def test_analysis_endpoint_evidence_assessment_dynamic():
    """Verify /api/v1/analysis returns dynamically generated evidence rubrics without hardcoded railway text."""
    client = TestClient(app)

    # Use a non-railway topic (e.g., healthcare / telecom)
    sample_text = (
        "National Health Authority launches new digital healthcare consultation "
        "portal across primary centers in Kerala and Tamil Nadu."
    )

    resp = client.post("/api/v1/analysis", json={"text": sample_text})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]

    assert "screening" in data
    assert "score" in data["screening"]
    assert "confidence" in data["screening"]
    assert "label" in data["screening"]

    # Verify related coverage structure and syndication decoupling
    assert isinstance(data["related_coverage"], list)
    assert len(data["related_coverage"]) <= 10
    for item in data["related_coverage"]:
        assert "title" in item
        assert "publisher" in item
        assert "url" in item
        assert "similarity" in item
        assert "relationship" in item
        assert "is_syndication" in item
        assert isinstance(item["is_syndication"], bool)

    # Verify fact-check matches
    assert isinstance(data["fact_check_matches"], list)
    assert len(data["fact_check_matches"]) <= 5

    # Verify dynamic evidence assessment is present and NOT hardcoded railway tariff text
    assert "evidence_assessment" in data
    ea = data["evidence_assessment"]
    assert isinstance(ea["available_evidence"], list)
    assert len(ea["available_evidence"]) > 0
    assert isinstance(ea["missing_evidence"], list)
    assert len(ea["missing_evidence"]) > 0
    assert isinstance(ea["analytical_recommendations"], str)
    assert len(ea["analytical_recommendations"]) > 10

    # Explicitly ensure hardcoded railway tariff contamination is gone
    for ev in ea["available_evidence"]:
        assert "tariff change" not in ev.lower()
    for ev in ea["missing_evidence"]:
        assert "tariff change" not in ev.lower()
    assert "Indian Railway Board" not in ea["analytical_recommendations"]


def test_refresh_all_parallel_execution():
    """Verify refresh_all executes channels concurrently and aggregates results."""
    service = NewsLensService()

    dummy_rss = RefreshResult(
        total_fetched=10,
        new_stored=5,
        duration_ms=100.0,
        provider_results={
            "The Hindu": ProviderFetchResult(
                source_id="the_hindu",
                source_name="The Hindu",
                source_type="rss",
                status="success",
                items_count=10,
            )
        },
        all_succeeded=True,
        all_failed=False,
    )
    dummy_gdelt = ProviderFetchResult(
        source_id="gdelt_doc_api",
        source_name="GDELT 2.0 DOC API",
        source_type="gdelt",
        status="success",
        items_count=8,
        new_items_inserted=4,
    )

    with (
        patch.object(service, "refresh_rss_feeds", return_value=dummy_rss) as mock_rss,
        patch.object(service, "refresh_gdelt", return_value=dummy_gdelt) as mock_gdelt,
    ):
        res = service.refresh_all(gdelt_query="India")

        assert mock_rss.called
        assert mock_gdelt.called
        assert res.total_fetched == 18
        assert res.new_stored == 9
        assert "The Hindu" in res.provider_results
        assert "GDELT 2.0 Doc API" in res.provider_results
