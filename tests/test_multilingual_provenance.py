"""Tests for multilingual article preservation, discovery provenance, and feed idempotency."""

from src.models import (
    NormalizedArticle,
    canonicalize_url,
    detect_text_language,
    generate_article_id,
)
from src.storage.database import DatabaseManager


def test_language_detection_and_indic_scripts():
    """Validates language detection across Devanagari, Bengali, and Latin scripts."""
    # Hindi Devanagari
    hi_text = "केंद्रीय गृह मंत्री श्री अमित शाह ने नई दिल्ली में संबोधित किया"
    assert detect_text_language(hi_text, fallback_lang="en") == "hi"

    # Marathi Devanagari with declared mr fallback
    assert detect_text_language(hi_text, fallback_lang="mr") == "mr"

    # Bengali
    bn_text = "মুখ্যমন্ত্রী মমতা বন্দ্যোপাধ্যায়ের নিরাপত্তা ব্যবস্থা বৃদ্ধি"
    assert detect_text_language(bn_text, fallback_lang="en") == "bn"
    assert detect_text_language(bn_text, fallback_lang="bn") == "bn"

    # English / Latin
    en_text = "Prime Minister addresses nation on economic reforms"
    assert detect_text_language(en_text, fallback_lang="en") == "en"
    assert (
        detect_text_language(en_text, fallback_lang="hi") == "hi"
    )  # fallback when no Indic script


def test_generate_article_id_multilingual_isolation():
    """Ensures same canonical URL in different languages produces distinct variant IDs,
    while English / default URLs preserve backwards-compatible SHA-256 hashes.
    """
    url = "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=2331363"

    id_en = generate_article_id(url, language="en", source_type="rss")
    id_hi = generate_article_id(url, language="hi", source_type="rss")
    id_mr = generate_article_id(url, language="mr", source_type="rss")

    # IDs must be distinct for distinct languages
    assert id_en != id_hi
    assert id_hi != id_mr
    assert id_en != id_mr

    # English ID matches expected legacy sha256(canonical_url) format
    canon = canonicalize_url(url)
    import hashlib

    legacy_hash = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
    assert id_en == f"rss_{legacy_hash}"


def test_multilingual_articles_preserved_distinctly(isolated_test_db):
    """Scenario 1: Same official press release published in English, Hindi, and Marathi
    with identical canonical URLs must be stored as 3 distinct article variants in SQLite.
    """
    db = DatabaseManager(db_path=isolated_test_db)
    shared_url = "https://pib.gov.in/PressReleasePage.aspx?PRID=999001"

    art_en = NormalizedArticle(
        id=generate_article_id(shared_url, language="en", source_type="rss"),
        title="Cabinet approves infrastructure project in Maharashtra",
        url=shared_url,
        publisher="Press Information Bureau (English)",
        published_at="2026-11-01T10:00:00Z",
        ingested_at="2026-11-01T10:05:00Z",
        source_type="rss",
        summary="English summary of the cabinet project.",
        language="en",
        country="IN",
        raw_metadata={"feed_id": "pib_english", "discovery_profile": "default"},
    )
    art_hi = NormalizedArticle(
        id=generate_article_id(shared_url, language="hi", source_type="rss"),
        title="मंत्रिमंडल ने महाराष्ट्र में अवसंरचना परियोजना को मंजूरी दी",
        url=shared_url,
        publisher="Press Information Bureau (Hindi)",
        published_at="2026-11-01T10:00:00Z",
        ingested_at="2026-11-01T10:05:00Z",
        source_type="rss",
        summary="परियोजना का हिंदी विवरण.",
        language="hi",
        country="IN",
        raw_metadata={"feed_id": "pib_hindi", "discovery_profile": "default"},
    )
    art_mr = NormalizedArticle(
        id=generate_article_id(shared_url, language="mr", source_type="rss"),
        title="मंत्रिमंडळाने महाराष्ट्रातील पायाभूत सुविधा प्रकल्पाला मंजुरी दिली",
        url=shared_url,
        publisher="Press Information Bureau (Marathi)",
        published_at="2026-11-01T10:00:00Z",
        ingested_at="2026-11-01T10:05:00Z",
        source_type="rss",
        summary="प्रकल्पाचा मराठी तपशील.",
        language="mr",
        country="IN",
        raw_metadata={"feed_id": "pib_marathi", "discovery_profile": "default"},
    )

    # Ingest batch
    initial_count = db.get_article_count()
    inserted = db.upsert_articles([art_en, art_hi, art_mr])
    assert inserted == 3, "All 3 language variants must be inserted as new articles"

    # Verify 3 distinct rows in database
    assert db.get_article_count() == initial_count + 3
    en_record = db.get_article_by_id(art_en.id)
    hi_record = db.get_article_by_id(art_hi.id)
    mr_record = db.get_article_by_id(art_mr.id)

    assert en_record is not None and en_record.language == "en"
    assert hi_record is not None and hi_record.language == "hi"
    assert mr_record is not None and mr_record.language == "mr"

    # Verify discovery provenance records for each variant
    en_disc = db.get_article_discoveries(art_en.id)
    assert len(en_disc) == 1
    assert en_disc[0]["provider_id"] == "pib_english"

    hi_disc = db.get_article_discoveries(art_hi.id)
    assert len(hi_disc) == 1
    assert hi_disc[0]["provider_id"] == "pib_hindi"

    mr_disc = db.get_article_discoveries(art_mr.id)
    assert len(mr_disc) == 1
    assert mr_disc[0]["provider_id"] == "pib_marathi"


def test_cross_provider_discovery_provenance(isolated_test_db):
    """Scenario 2 & 3: Same canonical article discovered across two distinct providers
    or feeds (e.g. PTI wire story syndicated to TOI, then rediscovered by Currents API).
    Must result in 1 article record and 2 distinct discovery observations.
    """
    db = DatabaseManager(db_path=isolated_test_db)
    canonical_wire_url = "https://www.presswire.in/reports/economic-growth-q3-2026"
    art_id = generate_article_id(canonical_wire_url, language="en", source_type="rss")

    # 1. First discovery via TOI RSS
    art_rss = NormalizedArticle(
        id=art_id,
        title="India Q3 GDP surges past forecasts",
        url=canonical_wire_url,
        publisher="The Times of India",
        published_at="2026-11-01T08:00:00Z",
        ingested_at="2026-11-01T08:05:00Z",
        source_type="rss",
        summary="GDP growth figures report.",
        language="en",
        country="IN",
        raw_metadata={"feed_id": "toi_national", "discovery_profile": "default"},
    )
    initial_count = db.get_article_count()
    first_inserted = db.upsert_articles([art_rss])
    assert first_inserted == 1
    assert db.get_article_count() == initial_count + 1

    # 2. Rediscovery via Currents API under currents_india profile
    art_currents = NormalizedArticle(
        id=art_id,  # identical article variant
        title="India Q3 GDP surges past forecasts",
        url=canonical_wire_url,
        publisher="Times of India Syndicate",
        published_at="2026-11-01T08:00:00Z",
        ingested_at="2026-11-01T08:30:00Z",
        source_type="currents",
        summary="GDP growth figures report.",
        language="en",
        country="IN",
        raw_metadata={"currents_id": "curr_12345", "discovery_profile": "currents_india"},
    )
    second_inserted = db.upsert_articles([art_currents])
    assert second_inserted == 0, "Rediscovered article should not create a second article row"
    assert db.get_article_count() == initial_count + 1

    # 3. Third discovery via Currents API under a different profile (currents_global)
    art_currents_global = NormalizedArticle(
        id=art_id,
        title="India Q3 GDP surges past forecasts",
        url=canonical_wire_url,
        publisher="Times of India Syndicate",
        published_at="2026-11-01T08:00:00Z",
        ingested_at="2026-11-01T08:45:00Z",
        source_type="currents",
        summary="GDP growth figures report.",
        language="en",
        country="IN",
        raw_metadata={"currents_id": "curr_12345", "discovery_profile": "currents_global"},
    )
    third_inserted = db.upsert_articles([art_currents_global])
    assert third_inserted == 0
    assert db.get_article_count() == initial_count + 1

    # Verify discovery provenance chain
    discoveries = db.get_article_discoveries(art_id)
    assert len(discoveries) == 3

    prov_profile_pairs = [(d["provider_id"], d["discovery_profile"]) for d in discoveries]
    assert ("toi_national", "default") in prov_profile_pairs
    assert ("currents", "currents_india") in prov_profile_pairs
    assert ("currents", "currents_global") in prov_profile_pairs


def test_ingestion_idempotency_and_zero_duplicate_discoveries(isolated_test_db):
    """Scenario 4 & 5: Repeated ingestion of the same feed produces 0 new articles
    and 0 duplicate discovery observations.
    """
    db = DatabaseManager(db_path=isolated_test_db)
    url = "https://indianexpress.com/article/india/isro-gaganyaan-update-2026"
    art_id = generate_article_id(url, language="en", source_type="rss")

    art = NormalizedArticle(
        id=art_id,
        title="ISRO completes Gaganyaan astronaut simulator trials",
        url=url,
        publisher="Indian Express (India)",
        published_at="2026-11-01T09:00:00Z",
        ingested_at="2026-11-01T09:02:00Z",
        source_type="rss",
        summary="Simulator trials completed successfully.",
        language="en",
        country="IN",
        raw_metadata={"feed_id": "indian_express_india", "discovery_profile": "default"},
    )

    # First ingestion
    initial_count = db.get_article_count()
    ins1 = db.upsert_articles([art])
    assert ins1 == 1
    assert db.get_article_count() == initial_count + 1
    assert len(db.get_article_discoveries(art_id)) == 1

    # Repeat 10 times
    for _ in range(10):
        ins_rep = db.upsert_articles([art])
        assert ins_rep == 0

    assert db.get_article_count() == initial_count + 1
    assert len(db.get_article_discoveries(art_id)) == 1
