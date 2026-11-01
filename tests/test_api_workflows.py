"""API workflows, endpoints integration, and contract tests for NewsLens India.

Verifies:
- Liveness and readiness health checks.
- Dashboard summary aggregation and provider health.
- Article query, search, filtering, and pagination.
- Article detail retrieval and 404 behavior.
- Manual article submission with origin tracking.
- Article analysis, ML screening, related coverage, and fact-check matching.
- Evidence search via BM25Plus retrieval.
- Multi-publisher coverage clusters and Cytoscape graph topology.
- Methodology specifications, metrics, and dataset split.
- Source ingestion status and refresh-all outcomes.
"""

from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient

from backend.main import app
from src.ingestion.models import ProviderFetchResult


def test_api_health_and_readiness(isolated_test_db):
    """Verify liveness and readiness probes return healthy responses."""
    client = TestClient(app)

    # 1. Liveness
    resp = client.get("/api/v1/health")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["status"] == "healthy"

    # 2. Readiness
    resp_ready = client.get("/api/v1/health/ready")
    assert resp_ready.status_code == status.HTTP_200_OK
    ready_data = resp_ready.json()["data"]
    assert ready_data["ready"] is True
    assert ready_data["database"] == "connected"


def test_api_dashboard_summary(isolated_test_db):
    """Verify dashboard summary aggregates articles, clusters, and provider telemetry."""
    client = TestClient(app)

    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]

    assert "total_articles" in data
    assert data["total_articles"] >= 30  # Seeded by isolated_test_db fixture
    assert "active_sources_count" in data
    assert "coverage_clusters_count" in data
    assert "fact_check_matches_count" in data
    assert isinstance(data["recent_articles"], list)
    assert len(data["recent_articles"]) > 0
    assert isinstance(data["source_statuses"], list)


def test_api_articles_listing_and_filtering(isolated_test_db):
    """Verify paginated article listing with source filtering and keyword search."""
    client = TestClient(app)

    # 1. Default listing
    resp = client.get("/api/v1/articles?page=1&page_size=10")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert len(data["items"]) <= 10
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["total_items"] >= 30

    # 2. Filter by source_type=rss
    resp_rss = client.get("/api/v1/articles?source_type=rss&page=1&page_size=50")
    assert resp_rss.status_code == status.HTTP_200_OK
    rss_items = resp_rss.json()["data"]["items"]
    assert all(a["source_type"] == "rss" for a in rss_items)

    # 3. Filter by keyword query
    resp_search = client.get("/api/v1/articles?query=Elections")
    assert resp_search.status_code == status.HTTP_200_OK
    search_items = resp_search.json()["data"]["items"]
    assert all(
        "elections" in a["title"].lower() or "elections" in a["summary"].lower()
        for a in search_items
    )

    # 4. Sorting
    resp_oldest = client.get("/api/v1/articles?sort_order=Oldest&page=1&page_size=10")
    assert resp_oldest.status_code == status.HTTP_200_OK


def test_api_article_detail_and_404(isolated_test_db):
    """Verify fetching single article details by ID and proper 404 response."""
    client = TestClient(app)

    # Fetch first article from list
    list_resp = client.get("/api/v1/articles?page=1&page_size=1")
    article_id = list_resp.json()["data"]["items"][0]["id"]

    # 1. Existing article
    resp = client.get(f"/api/v1/articles/{article_id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["id"] == article_id
    assert "title" in data
    assert "publisher" in data

    # 2. Non-existent article
    resp_404 = client.get("/api/v1/articles/nonexistent-id-99999")
    assert resp_404.status_code == status.HTTP_404_NOT_FOUND
    error = resp_404.json()["error"]
    assert error["code"] == "ARTICLE_NOT_FOUND"


def test_api_manual_article_submission(isolated_test_db):
    """Verify manual submission endpoint creates article with origin=manual."""
    client = TestClient(app)

    payload = {
        "title": "Investigative Analysis: Special Railway Budget Circular",
        "publisher": "Civic Tribune",
        "url": "https://example.com/civic-investigation-101",
        "summary": "Independent review of railway budget notifications and concession clauses.",
    }

    resp = client.post("/api/v1/articles", json=payload)
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()["data"]
    assert data["title"] == payload["title"]
    assert data["publisher"] == payload["publisher"]
    assert data["source_type"] == "manual"

    # Confirm it can be retrieved via article detail
    detail_resp = client.get(f"/api/v1/articles/{data['id']}")
    assert detail_resp.status_code == status.HTTP_200_OK
    assert detail_resp.json()["data"]["title"] == payload["title"]


def test_api_analysis_screening_workflow(isolated_test_db):
    """Verify article analysis returns ML screening, related coverage, and fact-checks."""
    client = TestClient(app)

    claim_text = (
        "Ministry of Railways has announced an immediate fare hike across all express trains "
        "effective from tomorrow morning with immediate suspension of concessions."
    )

    resp = client.post("/api/v1/analysis", json={"text": claim_text})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]

    assert data["input_text"] == claim_text
    assert "screening" in data
    assert "label" in data["screening"]
    assert "confidence" in data["screening"]
    assert "is_uncertain" in data["screening"]
    assert "decision_threshold" in data["screening"]
    assert "influential_tokens" in data["screening"]
    assert isinstance(data["related_coverage"], list)
    assert isinstance(data["fact_check_matches"], list)


def test_api_analysis_empty_input_validation(isolated_test_db):
    """Verify empty or short text violates validation constraints and returns 422."""
    client = TestClient(app)

    resp = client.post("/api/v1/analysis", json={"text": "   "})
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body or "error" in body


def test_api_evidence_search_bm25_plus(isolated_test_db):
    """Verify evidence retrieval via BM25Plus matching."""
    client = TestClient(app)

    # 1. Search for a query that matches railway fact-checks
    resp = client.post(
        "/api/v1/evidence/search", json={"query": "railway train fare concession", "top_k": 3}
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["query"] == "railway train fare concession"
    assert isinstance(data["matches"], list)

    # 2. Search for completely unrelated query (vocabulary overlap guard should yield empty matches)
    resp_unrelated = client.post(
        "/api/v1/evidence/search",
        json={"query": "astrophysics quantum gravitational singularity supernova", "top_k": 3},
    )
    assert resp_unrelated.status_code == status.HTTP_200_OK
    assert len(resp_unrelated.json()["data"]["matches"]) == 0


def test_api_coverage_clusters_and_graph(isolated_test_db):
    """Verify coverage clustering and Cytoscape graph topology endpoints."""
    client = TestClient(app)

    # 1. Clusters
    resp_clusters = client.get("/api/v1/coverage/clusters?limit=20")
    assert resp_clusters.status_code == status.HTTP_200_OK
    clusters = resp_clusters.json()["data"]
    assert isinstance(clusters, list)

    # 2. Graph topology
    resp_graph = client.get("/api/v1/coverage/graph?limit=20")
    assert resp_graph.status_code == status.HTTP_200_OK
    graph = resp_graph.json()["data"]
    assert "nodes" in graph
    assert "edges" in graph
    assert isinstance(graph["nodes"], list)
    assert isinstance(graph["edges"], list)


def test_api_methodology_endpoint(isolated_test_db):
    """Verify methodology blueprint returns architecture, empirical metrics, and limitations."""
    client = TestClient(app)

    resp = client.get("/api/v1/methodology")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]

    assert "pipeline_stages" in data
    assert len(data["pipeline_stages"]) >= 4
    assert "performance_metrics" in data
    assert "dataset_split" in data
    assert data["dataset_split"]["total_articles"] > 0
    assert "limitations" in data
    assert len(data["limitations"]) >= 6


def test_api_ingestion_status_endpoint(isolated_test_db):
    """Verify ingestion status returns statuses for all registered providers."""
    client = TestClient(app)

    resp = client.get("/api/v1/ingestion/status")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert "source_statuses" in data
    source_statuses = data["source_statuses"]
    assert isinstance(source_statuses, list)
    assert len(source_statuses) >= 7

    source_names = [s["source_name"].lower() for s in source_statuses]
    assert any("hindu" in s for s in source_names)
    assert any("gdelt" in s for s in source_names)
    assert any("deccan" in s for s in source_names)


def test_api_ingestion_refresh_mocked(isolated_test_db):
    """Verify ingestion refresh triggers all active providers and reports honest outcomes."""
    client = TestClient(app)

    mock_rss_result = {
        "the-hindu": ProviderFetchResult(
            source_id="the-hindu",
            source_name="The Hindu",
            source_type="rss",
            status="success",
            items_count=2,
            articles=[],
            http_status=200,
        )
    }

    mock_gdelt_success = ProviderFetchResult(
        source_id="gdelt",
        source_name="GDELT 2.0 DOC API",
        source_type="gdelt",
        status="success",
        items_count=3,
        articles=[],
        http_status=200,
    )

    with (
        patch(
            "src.ingestion.rss.RssIngestionService.fetch_all", return_value=mock_rss_result
        ) as mock_rss,
        patch(
            "src.ingestion.gdelt.GdeltClient.fetch_articles", return_value=mock_gdelt_success
        ) as mock_gdelt,
    ):
        resp = client.post("/api/v1/ingestion/refresh", json={"source_type": "all"})
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()["data"]
        assert "total_fetched" in data
        assert "summary" in data
        assert "all_succeeded" in data
        assert mock_rss.called
        assert mock_gdelt.called
