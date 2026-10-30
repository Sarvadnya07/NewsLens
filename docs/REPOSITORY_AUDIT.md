# REPOSITORY AUDIT: Research Codebase Inspection Report

**Date of Audit:** October 30, 2026  
**Auditor:** Senior Autonomous Software Engineer / NewsLens India Integration Lead  
**Scope:** `research/` directory inspection prior to architectural integration into `NewsLens India`.

---

## Executive Summary

The workspace includes 4 open-source reference repositories under `research/`:
1. `research/gdelt-doc-api`: Python client wrapper for GDELT 2.0 Doc API.
2. `research/feedparser`: Mature RSS/Atom syndication parser.
3. `research/fake-news-detection`: Reference ML project using LIAR benchmark dataset with scikit-learn models.
4. `research/rank_bm25`: Native Python implementation of BM25 family ranking algorithms (Okapi BM25, BM25L, BM25+).

None of these repositories should be blindly copied or vendored into root. Instead:
- `feedparser` and `rank_bm25` are mature PyPI packages already installed in the target Python 3.13 environment.
- `gdelt-doc-api` provides request templates and filter patterns, but requires defensive error/rate-limit handling (status 429 throttling mitigation, exponential backoff, safe timeouts).
- `fake-news-detection` demonstrates NLP feature extraction and classification with LIAR, but existing saved model files (`final_model.sav`, `model.pkl`) must NOT be loaded directly due to security and pickle compatibility across Python versions. We will train a reproducible, leak-free Scikit-learn TF-IDF + Logistic Regression pipeline and save verified Joblib artifacts.
- `rank_bm25` will be utilized to implement BM25Okapi retrieval for authentic Indian fact-checking claims.

---

## 1. Repository: `research/gdelt-doc-api`

### 1.1 Overview
- **Purpose:** Fetches news article metadata and volume timelines from the GDELT 2.0 Doc API (`https://api.gdeltproject.org/api/v2/doc/doc`).
- **Primary Source Files:**
  - `gdeltdoc/api_client.py`: Implements `GdeltDoc` class and query execution.
  - `gdeltdoc/filters.py`: Implements `Filters` class compiling query parameter strings (keyword, country, sourcelang, domain, timespan, maxrecords).
  - `gdeltdoc/helpers.py`: JSON cleaning and date formatting.
  - `gdeltdoc/errors.py`: Custom HTTP/API exception handling.

### 1.2 Dependencies & Python Compatibility
- **Dependencies:** `pandas>=2.2.3`, `requests>=2.32.3`, `typing_extensions>=4.13.0`.
- **Python Compatibility:** Python >=3.10 (tested and compatible with Python 3.13).
- **License:** MIT License (Copyright (c) 2020 Alex Whitehead-Smith).

### 1.3 Useful Classes & Functions
- `Filters(keyword=..., country=..., language=..., timespan=..., num_records=...)`: Query builder.
- `GdeltDoc.article_search(Filters)`: Fetches normalized DataFrame with columns: `url`, `url_mobile`, `title`, `seendate`, `socialimage`, `domain`, `language`, `sourcecountry`.

### 1.4 Risks & Security Issues
- **Rate Limiting:** GDELT API returns HTTP 429 ("Please limit requests to one every 5 seconds") if hit rapidly.
- **Unstable JSON / HTML error responses:** GDELT frequently returns 200 OK with HTML error text rather than JSON when malformed queries are submitted.
- **Network Outages & Latency:** Inability to reach remote GDELT endpoints must not crash the application.
- **Action for NewsLens:** Implement `src/ingestion/gdelt.py` with custom retry/rate-limit backoff, request timeout limits (8-10s), fallback to cached/sample records, and strict data schema normalization into `NormalizedArticle`.

---

## 2. Repository: `research/feedparser`

### 2.1 Overview
- **Purpose:** Universal Feed Parser in Python for RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom, and JSON feeds.
- **Primary Source Files:** Full feedparser distribution package (`feedparser/`).
- **Dependencies:** `sgmllib3k` / `feedparser-sgmllib`.
- **Python Compatibility:** Python 3.8 - 3.13.
- **License:** BSD 2-Clause License (Copyright 2010-2026 Kurt McKee, Copyright 2002-2008 Mark Pilgrim).

### 2.2 Reuse Opportunities & Decision
- **Installed Status:** `feedparser 6.0.14` is already installed in the Python environment.
- **Action for NewsLens:** Do NOT vendor or copy `research/feedparser`. Directly `import feedparser` in `src/ingestion/rss.py`.
- **Feed Normalization:** Build multi-feed aggregation for major Indian publications (e.g., The Hindu, Times of India, NDTV, Indian Express, Press Information Bureau) with per-feed error isolation, sanitized timestamps, and fallback mechanisms.

---

## 3. Repository: `research/fake-news-detection`

### 3.1 Overview
- **Purpose:** Text classification model to detect fake vs true news statements using the LIAR benchmark dataset.
- **Primary Source Files:**
  - `DataPrep.py`: Reads train/test/valid sets and performs tokenization/stemming.
  - `FeatureSelection.py`: CountVectorizer, TfidfVectorizer, n-grams.
  - `classifier.py`: Evaluates Naive Bayes, Logistic Regression, SGD, SVM, and Random Forest.
  - `prediction.py`: Example interactive terminal CLI that unpickles `final_model.sav`.
  - Datasets: `train.csv` (10,240 records), `test.csv` (2,551 records), `valid.csv` (2,571 records).
  - Pretrained files: `final_model.sav`, `model.pkl`.

### 3.2 Dependencies & Python Compatibility
- **Dependencies:** `scikit-learn`, `numpy`, `pandas`, `nltk`, `seaborn`, `matplotlib`.
- **Python Compatibility:** Originally Python 3.6; scripts rely on deprecated APIs and legacy pickle protocols.
- **License:** MIT License (Copyright (c) 2018 Nishit Patel).

### 3.3 Security Issues & Artifact Integrity
- **CRITICAL RISK - Untrusted Pickles:** `final_model.sav` and `model.pkl` are binary pickle files created under Python 3.6 with legacy scikit-learn. Loading untrusted pickles can lead to arbitrary code execution and version incompatibility crashes on Python 3.13.
- **CRITICAL REQUIREMENT:** Discard existing binary pickle artifacts. Re-train a fresh, clean Scikit-learn TF-IDF + Logistic Regression model directly from the documented `train.csv` and evaluate against `test.csv`.
- **Action for NewsLens:** Implement:
  - `src/preprocessing/cleaner.py`: Text normalization, punctuation handling, URL stripping, stopword filtering.
  - `src/ml/train.py`: Leak-free pipeline fitting TF-IDF on train split only, training Logistic Regression, generating full evaluation metrics (Accuracy, Precision, Recall, Macro-F1, Confusion Matrix), and persisting modern `.joblib` model + vectorizer artifacts in `models/`.
  - `src/ml/predict.py`: Safe inference service providing probabilistic score, prediction class, and mandatory uncertainty disclosures.

---

## 4. Repository: `research/rank_bm25`

### 4.1 Overview
- **Purpose:** Pure Python implementation of BM25 ranking algorithms for information retrieval over tokenized text corpora.
- **Primary Source Files:**
  - `rank_bm25.py`: Classes `BM25`, `BM25Okapi`, `BM25L`, `BM25Plus`.
- **Dependencies:** `numpy`.
- **Python Compatibility:** Python >=3.6 (fully compatible with Python 3.13).
- **License:** Apache License 2.0 (Copyright 2019 Dorian Brown).

### 4.2 Reuse Opportunities & Decision
- **Installed Status:** `rank_bm25 0.2.2` is already installed in Python 3.13.
- **Action for NewsLens:** Import `rank_bm25.BM25Okapi` in `src/retrieval/fact_check.py`.
- **Fact-Check Indexing:** Index a verified collection of Indian fact-checks (PIB Fact Check, AltNews, BoomLive public claims) with original source provenance, verdict labels, review dates, and honest no-data fallback states when queries yield no high-confidence evidence.

---

## 5. Architectural Reuse Matrix

| Module | Source Reference | NewsLens Implementation | Reuse Mechanism |
|---|---|---|---|
| GDELT Ingestion | `research/gdelt-doc-api` | `src/ingestion/gdelt.py` | Adapted client with rate limiters, caching, and timeout guards |
| RSS Ingestion | `research/feedparser` | `src/ingestion/rss.py` | Direct import of installed `feedparser` package with multi-source config |
| Text Cleaner | `research/fake-news-detection/DataPrep.py` | `src/preprocessing/cleaner.py` | Cleaned regex & stopword normalization |
| ML Pipeline | `research/fake-news-detection/classifier.py` | `src/ml/train.py`, `src/ml/predict.py` | TF-IDF + Logistic Regression trained with joblib persistence |
| Fact Retrieval | `research/rank_bm25` | `src/retrieval/fact_check.py` | `rank_bm25.BM25Okapi` indexing curated fact-check claims |
| Deduplication | New implementation | `src/processing/deduplication.py` | TF-IDF cosine similarity + normalized title clustering |
| Storage | New implementation | `src/storage/database.py` | SQLite schema with parameterized queries & upsert logic |
| App Service | New implementation | `src/services/news_service.py` | Service layer unifying all ingestion, ml, and retrieval modules |
| Web UI | New implementation | `app.py` | Multi-page Streamlit dashboard |
