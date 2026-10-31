"""Comprehensive Phase 4 unit and integration tests for ML pipeline, evaluation metrics,
BM25 retrieval guards, and deduplication behavior in NewsLens India.
"""

import json
import os
from unittest.mock import patch

import joblib
import pytest

from src.ml.predict import FakeNewsScreeningModel
from src.ml.train import LIAR_COLUMNS, load_canonical_tsv, map_binary_label
from src.models import NormalizedArticle
from src.processing.deduplication import NewsDeduplicator
from src.retrieval.fact_check import FactCheckRetriever

# The canonical LIAR TSVs and the trained joblib artifacts are deliberately not
# committed (see .gitignore). Tests that need them skip with an explicit reason
# instead of failing a clean checkout, so CI still exercises the rest of the
# suite. Regenerate locally with `python -m src.ml.train` after fetching data/liar.
ARTIFACTS_PRESENT = os.path.exists("models/classifier.joblib") and os.path.exists(
    "models/tfidf_vectorizer.joblib"
)
LIAR_PRESENT = os.path.exists("data/liar/test.tsv")

requires_artifacts = pytest.mark.skipif(
    not ARTIFACTS_PRESENT, reason="trained joblib artifacts are not present (run src.ml.train)"
)
requires_liar = pytest.mark.skipif(
    not LIAR_PRESENT, reason="canonical LIAR TSVs are not present (see data/liar/PROVENANCE.md)"
)

# ---------------------------------------------------------------------------
# 1. Dataset Schema & Label Mapping Tests
# ---------------------------------------------------------------------------


@requires_liar
def test_canonical_tsv_parsing():
    """Verify loading canonical TSV parsing handles quotes without row collapse."""
    tsv_path = "data/liar/test.tsv"
    assert os.path.exists(tsv_path), "LIAR test.tsv missing"
    df = load_canonical_tsv(tsv_path)
    assert len(df) == 1283
    assert list(df.columns) == LIAR_COLUMNS
    assert df["statement"].str.len().min() > 0


def test_label_mapping_consistency():
    """Verify that all 6 LIAR labels map deterministically to binary classes."""
    # Higher-veracity group: half-true, mostly-true, true -> Class 1
    assert map_binary_label("true") == 1
    assert map_binary_label("mostly-true") == 1
    assert map_binary_label("half-true") == 1
    assert map_binary_label("1") == 1
    assert map_binary_label("t") == 1

    # Lower-veracity group: barely-true, false, pants-fire -> Class 0
    assert map_binary_label("barely-true") == 0
    assert map_binary_label("false") == 0
    assert map_binary_label("pants-fire") == 0
    assert map_binary_label("unknown") == 0
    assert map_binary_label("") == 0


def test_no_duplicate_leakage_in_metrics():
    """Verify evaluation metrics document duplicate statement exclusions."""
    metrics_path = "models/evaluation_metrics.json"
    assert os.path.exists(metrics_path)
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    dup_stats = metrics.get("duplicate_leaks_removed", {})
    assert dup_stats.get("test_partition", 0) == 5
    assert dup_stats.get("validation_partition", 0) == 7
    assert dup_stats.get("total", 0) == 12
    assert metrics["official_test_samples"] == 1278


# ---------------------------------------------------------------------------
# 2. Model Artifact Integrity & Compatibility Tests
# ---------------------------------------------------------------------------


@requires_artifacts
def test_model_artifacts_compatibility():
    """Check that classifier and vectorizer feature dimensions match and are compatible."""
    vec_path = "models/tfidf_vectorizer.joblib"
    clf_path = "models/classifier.joblib"
    assert os.path.exists(vec_path)
    assert os.path.exists(clf_path)

    vec = joblib.load(vec_path)
    clf = joblib.load(clf_path)

    assert len(vec.get_feature_names_out()) == 10000
    assert clf.coef_.shape == (1, 10000)
    assert list(clf.classes_) == [0, 1]


def test_missing_artifacts_graceful_handling():
    """Ensure missing model artifacts return a clean error state without crashing."""
    model = FakeNewsScreeningModel(
        vectorizer_path="nonexistent/vec.joblib",
        classifier_path="nonexistent/clf.joblib",
    )
    assert model.is_ready is False
    res = model.predict("Breaking news headline.")
    assert res["status"] == "error"
    assert "not loaded" in res["error"]
    assert res["confidence"] == 0.0


# ---------------------------------------------------------------------------
# 3. Prediction Semantics & Output Handling Tests
# ---------------------------------------------------------------------------


@requires_artifacts
def test_prediction_labels_and_scores():
    """Verify predict output uses responsible AI linguistic signal labels."""
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    res = model.predict("Prime Minister announces infrastructure grant in parliament.")
    assert res["status"] == "success"
    assert res["label"] in [
        "Higher-veracity linguistic pattern",
        "Lower-veracity linguistic pattern",
    ]
    assert "model_score" in res
    assert 0.0 <= res["model_score"] <= 1.0
    assert "Model Advisory:" in res["uncertainty_note"]
    assert "US political LIAR benchmark" in res["uncertainty_note"]
    assert isinstance(res["tokens"], list)


@requires_artifacts
def test_prediction_uncertainty_flag():
    """Verify that predictions near 50/50 decision boundary are flagged as uncertain."""
    model = FakeNewsScreeningModel()
    assert model.is_ready is True

    # Mock predict_proba to return 0.52 and 0.48 (margin < 0.15)
    with patch.object(model.classifier, "predict_proba", return_value=[[0.52, 0.48]]):
        res = model.predict("Ambiguous statement with minimal lexical cues.")
        assert res["status"] == "success"
        assert res["is_uncertain"] is True
        assert "Uncertain / Insufficient Signal" in res["uncertainty_note"]


# ---------------------------------------------------------------------------
# 4. Evaluation Consistency & Confusion Matrix Tests
# ---------------------------------------------------------------------------


def test_evaluation_metrics_mathematical_consistency():
    """Recalculate metrics directly from the confusion matrix to ensure honesty."""
    with open("models/evaluation_metrics.json", "r", encoding="utf-8") as f:
        metrics = json.load(f)

    cm = metrics["confusion_matrix"]
    assert len(cm) == 2 and len(cm[0]) == 2
    # Row 0: True Fake (0), Col 0: Pred Fake, Col 1: Pred True
    # Row 1: True True (1), Col 0: Pred Fake, Col 1: Pred True
    tn, fp = cm[0][0], cm[0][1]
    fn, tp = cm[1][0], cm[1][1]

    total = tn + fp + fn + tp
    assert total == metrics["official_test_samples"]

    calc_acc = (tp + tn) / total
    assert pytest.approx(calc_acc, abs=1e-5) == metrics["accuracy"]

    prec_fake = tn / (tn + fn)
    rec_fake = tn / (tn + fp)
    f1_fake = 2 * prec_fake * rec_fake / (prec_fake + rec_fake)

    prec_true = tp / (tp + fp)
    rec_true = tp / (tp + fn)
    f1_true = 2 * prec_true * rec_true / (prec_true + rec_true)

    macro_prec = (prec_fake + prec_true) / 2
    macro_rec = (rec_fake + rec_true) / 2
    macro_f1 = (f1_fake + f1_true) / 2

    assert pytest.approx(macro_prec, abs=1e-5) == metrics["macro_precision"]
    assert pytest.approx(macro_rec, abs=1e-5) == metrics["macro_recall"]
    assert pytest.approx(macro_f1, abs=1e-5) == metrics["macro_f1"]


# ---------------------------------------------------------------------------
# 5. BM25 Fact-Check Retrieval & Provenance Tests
# ---------------------------------------------------------------------------


def test_fact_check_retrieval_provenance_and_guards():
    """Verify BM25 retrieval returns exact provenance and rejects zero-overlap queries."""
    retriever = FactCheckRetriever()
    assert retriever.total_records == 8

    # Query with known keywords from pib_002
    results = retriever.retrieve("RBI currency notes 500 legal tender", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert "RBI" in top["claim"] or "500" in top["claim"]
    assert top["fact_checker"] == "PIB Fact Check (India)"
    assert top["source_url"].startswith("http")
    assert top["relevance_score"] > 1.0

    # Zero-overlap query must return empty list (not floor score false-positive)
    zero_overlap = retriever.retrieve("Quantum computing teleportation in interstellar physics")
    assert zero_overlap == []


# ---------------------------------------------------------------------------
# 6. News Deduplication & Coverage Clustering Tests
# ---------------------------------------------------------------------------


def test_deduplicator_classification_thresholds():
    """Verify deduplicator correctly categorizes similarity tiers."""
    dedup = NewsDeduplicator(exact_threshold=0.90, similar_threshold=0.55)

    assert dedup.classify_relationship(0.95) == "exact_or_republished"
    assert dedup.classify_relationship(0.75) == "likely_syndicated"
    assert dedup.classify_relationship(0.60) == "similar_coverage"
    assert dedup.classify_relationship(0.30) == "unrelated"


def test_deduplicator_clusters_preservation():
    """Verify clustering preserves original publishers and URLs."""
    dedup = NewsDeduplicator(exact_threshold=0.90, similar_threshold=0.55)

    articles = [
        NormalizedArticle(
            id="1",
            title="Finance Minister presents Annual Union Budget in Parliament today",
            url="https://thehindu.com/budget-2026",
            publisher="The Hindu",
            published_at="2026-02-01T10:00:00Z",
            ingested_at="2026-02-01T10:05:00Z",
            source_type="rss",
        ),
        NormalizedArticle(
            id="2",
            title="Finance Minister presents Annual Union Budget in Parliament live",
            url="https://timesofindia.com/budget-2026",
            publisher="The Times of India",
            published_at="2026-02-01T10:02:00Z",
            ingested_at="2026-02-01T10:06:00Z",
            source_type="rss",
        ),
        NormalizedArticle(
            id="3",
            title="Monsoon rains arrive early in Kerala coast",
            url="https://ndtv.com/monsoon",
            publisher="NDTV",
            published_at="2026-06-01T10:00:00Z",
            ingested_at="2026-06-01T10:05:00Z",
            source_type="rss",
        ),
    ]

    clusters = dedup.find_related_and_duplicates(articles)
    assert len(clusters) == 2  # 1 budget cluster + 1 weather cluster

    budget_cluster = next(c for c in clusters if "Budget" in c["primary_article"].title)
    assert len(budget_cluster["publishers"]) == 2
    assert "The Hindu" in budget_cluster["publishers"]
    assert "The Times of India" in budget_cluster["publishers"]
