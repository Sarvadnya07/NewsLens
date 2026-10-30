# NewsLens India

> **Near-Real-Time Indian News Monitoring and Misinformation Screening Using Multi-Source Evidence, BM25 Retrieval, and Machine Learning.**

---

## 🌟 Key Capabilities

1. **Indian News Discovery & Monitoring:** Aggregates live syndicated feeds from leading Indian national publishers (*The Times of India, The Hindu, NDTV, Indian Express, Hindustan Times, Livemint*) with per-source network failure isolation.
2. **GDELT 2.0 Document Querying:** Direct topic exploration across GDELT's global document collection with automatic India country (`sourcecountry:IN`) and English language filters, fortified with a 5-second rate-limiting throttle.
3. **Manual Article Registration:** Submit custom headlines, social claims, or URLs for database indexing and screening.
4. **Leak-Free Machine Learning Screening:** Scikit-learn TF-IDF + Logistic Regression pipeline trained with duplicate leakage elimination, providing probabilistic suspicion scores and responsible AI uncertainty disclosures.
5. **Authentic Fact-Check Candidate Retrieval:** BM25Plus retrieval over verified Indian claims from accredited watchdogs (*PIB Fact Check, BOOM Live, Alt News*) with direct links and verdicts.
6. **Cross-Publisher Duplicate & Cluster Detection:** Discovers multi-outlet coverage and duplicates using character/word n-gram TF-IDF cosine similarity.
7. **Thread-Safe SQLite Persistence:** Parameterized schema storing normalized articles and source health metrics.
8. **Interactive Streamlit Web Dashboard:** Modular multi-page UI architecture with responsive cards, theme styling, and safe HTML escaping.

---

## 🏛️ Architecture

```
NewsLens-India/
├── .venv/                      # Canonical Python 3.12 project-local virtual environment
├── app.py                      # Streamlit application entrypoint
├── requirements.txt            # Direct declared dependencies
├── requirements-lock.txt       # Frozen environment lockfile
├── pyproject.toml              # Ruff and formatting configuration
├── pytest.ini                  # Pytest configuration
├── THIRD_PARTY_NOTICES.md      # Attribution & licenses for reference repositories
├── docs/
│   ├── ENVIRONMENT_AUDIT.md    # Python interpreter & environment audit
│   ├── VERIFICATION_REPORT.md  # 20-test passing verification report
│   ├── ENGINEERING_AUDIT.md    # Defect log & hardening report
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
│   ├── services/
│   │   └── news_service.py     # Central orchestration layer
│   └── ui/                     # Modular frontend UI components and pages
│       ├── components.py       # Reusable editorial cards & headers
│       ├── navigation.py       # Sidebar navigation and state manager
│       ├── theme.py            # Typography and custom styling
│       └── pages/              # Dedicated page renderers
│           ├── dashboard.py
│           ├── news_monitor.py
│           ├── article_analysis.py
│           ├── evidence_coverage.py
│           └── methodology.py
└── tests/
    ├── test_all.py             # 16 unit & integration tests
    └── test_ui.py              # 4 Streamlit AppTest headless UI tests
```

---

## 🚀 Quickstart & Reproduction Commands

### 1. Environment Setup (Windows CMD / PowerShell)
Create the dedicated project-local virtual environment using Python 3.12:

```cmd
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Linting & Formatting Check
```cmd
.venv\Scripts\python.exe -m ruff check src tests app.py
.venv\Scripts\python.exe -m ruff format --check src tests app.py
```

### 3. Run Test Suite (20 Tests)
```cmd
.venv\Scripts\python.exe -m pytest -v
```

### 4. Launch Streamlit Application
```cmd
.venv\Scripts\python.exe -m streamlit run app.py
```
*The web dashboard opens at `http://localhost:8501`.*

---

## 📊 ML Evaluation Summary

- **Benchmark:** LIAR Dataset (`research/fake-news-detection/`)
- **Training Samples:** 10,240 | **Held-out Test Samples:** 2,539
- **Accuracy:** `61.80%`
- **Macro F1:** `0.6158`
- **Misleading Class F1:** `0.5869`
- *Note: Statistical ML screening indicates stylistic linguistic patterns. It is not an automated fact-checker.*
