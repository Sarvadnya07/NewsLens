# NewsLens India

> **Near-Real-Time Indian News Monitoring and Misinformation Screening Using Multi-Source Evidence, BM25 Retrieval, and Machine Learning.**

---

## 🌟 Key Capabilities

1. **Indian News Discovery & Monitoring:** Aggregates live syndicated feeds from leading Indian national publishers (*The Times of India, The Hindu, NDTV, Indian Express, Hindustan Times*) with per-source network failure isolation.
2. **GDELT 2.0 Document Querying:** Direct topic exploration across GDELT's global document collection with automatic India country (`sourcecountry:IN`) and English language filters, fortified with a 5-second rate-limiting throttle.
3. **Manual Article Registration:** Submit custom headlines, social claims, or URLs for database indexing and screening.
4. **Leak-Free Machine Learning Screening:** Scikit-learn TF-IDF + Logistic Regression pipeline trained with duplicate leakage elimination, providing probabilistic suspicion scores and responsible AI uncertainty disclosures.
5. **Authentic Fact-Check Candidate Retrieval:** BM25Plus retrieval over verified Indian claims from accredited watchdogs (*PIB Fact Check, BOOM Live, Alt News*) with direct links and verdicts.
6. **Cross-Publisher Duplicate & Cluster Detection:** Discovers multi-outlet coverage and duplicates using character/word n-gram TF-IDF cosine similarity.
7. **Thread-Safe SQLite Persistence:** Parameterized schema storing normalized articles and source health metrics.
8. **Interactive Streamlit Web Dashboard:** Modern 5-tab application built for live academic demonstrations.

---

## 🏛️ Architecture

```
NewsLens-India/
├── app.py                      # Interactive Streamlit 5-page dashboard
├── requirements.txt            # Pinned working dependencies
├── pytest.ini                  # Pytest configuration
├── THIRD_PARTY_NOTICES.md      # Attribution & licenses for reference repositories
├── docs/
│   ├── REPOSITORY_AUDIT.md     # Phase 1 deep-dive audit of all 4 research repos
│   ├── ML_EVALUATION_REPORT.md # Reproducible metrics and confusion matrix
│   └── DATASET_AUDIT.md        # LIAR benchmark and fact-check governance audit
├── data/
│   ├── newslens.db             # SQLite database storing normalized articles
│   └── fact_checks.json        # Curated authentic Indian fact-check catalog
├── models/
│   ├── tfidf_vectorizer.joblib # Trained TF-IDF vectorizer artifact
│   ├── classifier.joblib       # Trained Logistic Regression classifier
│   └── evaluation_metrics.json # Full evaluation JSON output
├── src/
│   ├── models.py               # NormalizedArticle & FactCheckRecord dataclasses
│   ├── ingestion/
│   │   ├── gdelt.py            # GDELT 2.0 Doc API client with rate-limiting
│   │   └── rss.py              # Multi-publisher RSS aggregator
│   ├── preprocessing/
│   │   └── cleaner.py          # URL/HTML stripping, stopword & regex cleaner
│   ├── ml/
│   │   ├── train.py            # Reproducible model training pipeline
│   │   └── predict.py          # Inference engine with uncertainty disclaimers
│   ├── retrieval/
│   │   └── fact_check.py       # BM25Plus retrieval over accredited fact checks
│   ├── processing/
│   │   └── deduplication.py    # TF-IDF cosine clustering & relationship discovery
│   ├── storage/
│   │   └── database.py         # SQLite CRUD with parameterized queries
│   └── services/
│       └── news_service.py     # Central orchestration layer
└── tests/
    └── test_all.py             # 13 automated tests across all modules
```

---

## 🚀 Quickstart & Launch Command

### 1. Requirements
Ensure Python 3.10+ is installed (tested on Python 3.13):
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m pytest -v
```

### 3. Launch Streamlit Application
```bash
streamlit run app.py
```
*The web dashboard will open automatically in your browser at `http://localhost:8501`.*

---

## 📊 ML Evaluation Summary

- **Benchmark:** LIAR Dataset (`research/fake-news-detection/`)
- **Training Samples:** 10,240 | **Held-out Test Samples:** 2,539
- **Accuracy:** `61.80%`
- **Macro F1:** `0.6158`
- **Suspect Class F1:** `0.5869`
- *Note: As emphasized across the app, statistical ML screening is an indicator of linguistic cues, not a substitute for fact-checking.*

---

## ⚠️ Limitations & Future Work

- **Linguistic Screening Scope:** The classifier flags sensationalist and misleading text patterns, but cannot independently verify uncorroborated breaking real-time news without external sources.
- **GDELT Rate Limits:** The public GDELT Doc API strictly enforces a 5-second interval per client IP; high-frequency parallel polling must be avoided.
- **Vernacular Language Support:** Current NLP processing focuses on English; regional Indian language models (Hindi, Tamil, Bengali) represent a natural roadmap enhancement.
