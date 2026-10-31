# Final System Repair & Acceptance Audit Report: NewsLens India

**Project Title:** NewsLens India — Near-Real-Time Indian News Monitoring and Misinformation Screening  
**Module:** Phase 5 Full Integration, Regression Testing & Project Acceptance  
**Date:** October 31, 2026  
**Auditor / Lead:** Final Integration & Acceptance Technical Lead  
**Operating Environment:** Windows, Python 3.12.10 (`.venv`), Streamlit 1.43.2  
**Current Git State:** Branch `master`, commit `e854ab2`  
**Overall Acceptance Decision:** **READY (Fully Verified & Operational)**  

---

## 1. Executive Summary

A comprehensive, multi-phase forensic audit and engineering remediation was conducted across the NewsLens India repository. 

Prior to this remediation, the platform exhibited significant defects:
1. **Broken News Monitor:** Displayed 0 records by default despite hundreds of stored articles due to query parameter collisions and case-sensitive publisher filters.
2. **Fabricated UI Mockups & Synthetic Data:** Wireframe artifacts (such as mock claim `#NL-2024-884`, arbitrary 99.8% certainty badges, fake railway gazettes, fabricated OCR scans, and static feature token cards like `URGENT +0.42`) were presented as live application features.
3. **Fragile Ingestion & Persistence:** Unbounded streaming downloads in RSS parsers, uncaught timeouts and rate limits in GDELT clients, unescaped SQL LIKE wildcards (`%` and `_`), and non-isolated network errors.
4. **Epistemic Label Overreach:** The ML classifier claimed "Verified True" or "Misinformation Detected", conflating heuristic lexical patterns learned from the US political LIAR benchmark with factual truth determinations.
5. **Methodology Inconsistencies:** The methodology page asserted unimplemented features, including 48,000-vocabulary feature dimensions, SAGA solvers, Indic script normalization, Named Entity Recognition (NER v4), live microservices, and automated IFCN synchronization.

Through systematic execution of Phases 1 through 5, all modules were brought into complete alignment with code reality:
- **Every metric and card reflects real application state.**
- **54 automated unit, integration, and UI tests pass deterministically.**
- **Code complies with zero Ruff lint and format violations.**
- **Bandit AST security checks pass with zero High/Medium vulnerabilities.**
- **The SQLite datastore remains pristine at 819 verified articles and 7 source status records.**

---

## 2. Complete System Architecture & Ingestion Flow

The complete, verified application pipeline is structured as follows:

```text
Configured National RSS (6 Feeds) ──┐
                                     ├──> Bounded Streaming (5MB limit, 10s timeout, SSRF safe) ──┐
GDELT 2.0 Doc API (India, English) ──┘                                                            │
                                                                                                  ├──> URL Canonicalization & Normalization
User Query / Manual Text Submission ─────────────────────────────────────────────────────────────┘                     │
                                                                                                                        ├──> Thread-Safe SQLite WAL Store (819 Articles)
News Monitor Page <─────────────────────────────────────────────────────────────────────────────────────────────────────┤
                                                                                                                        ├──> NewsLensService Orchestration
User Text Input ──> Text Sanitization (`clean_text`) ──> Scikit-Learn TF-IDF (10k) ──> Logistic Regression ──> Linguistic Screening Signal (Analyze Article)
                                                                                                                        │
Claim Text ──> Tokenization ──> Pre-Scoring Vocab Overlap Guard ──> Rank-BM25Plus ──> Local Fact-Check Candidates (8 Cases)
                                                                                                                        │
Headline / Article Body ──> Sublinear TF-IDF (1, 2-grams) ──> Cosine Similarity ──> Multi-Source Coverage Clustering (Evidence & Coverage)
```

---

## 3. Detailed Component Audits & Verifications

### 3.1 Backend & Ingestion Tier
- **RSS Ingestion (`src/ingestion/rss.py`):**
  - Configured with 6 national publishers (*Times of India, The Hindu, NDTV, Indian Express, Hindustan Times, Livemint*).
  - Enforces streaming chunked downloads (`stream=True`) with a strict **5MB byte ceiling**, **10-second socket timeout**, safe redirect limits (`max_redirects=4`), and SSRF netloc guards blocking loopback and private IP blocks (`127.0.0.1`, `10.*`, `192.168.*`, `169.254.*`).
  - Implements per-source failure isolation; transient network or parsing failures on one feed do not abort the ingestion run or wipe healthy feed status records.
- **GDELT 2.0 Integration (`src/ingestion/gdelt.py`):**
  - Rate-throttled via a 5.0-second interval guard.
  - Handles HTTP 429 rate limits, HTTP 5xx errors, payload decode failures, and connection timeouts with exponential backoff retries.
  - Returns structured `ProviderFetchResult` models with typed `ProviderError` hierarchies.

### 3.2 Database & Persistence Tier (`src/storage/database.py`)
- **Engine:** SQLite 3 in Write-Ahead Logging (`WAL`) mode with `busy_timeout=5000` ms.
- **Schema & Upsert:** Unique index on canonicalized `url` with parameterized `INSERT OR REPLACE` upserts, preserving ingestion timestamps.
- **Search & Wildcard Safety:** Literal `%` and `_` characters in user search queries are escaped using `ESCAPE '\'` to prevent uncontrolled full-table wildcard scans.
- **Decoupled Pagination:** Total record counts and paginated article subsets are computed using decoupled, thread-safe queries.
- **Integrity Baseline:** Verified at **819 articles** and **7 source status records** in `data/newslens.db`.

### 3.3 Machine Learning Pipeline (`src/ml/train.py`, `src/ml/predict.py`)
- **Dataset:** Canonical LIAR benchmark (Wang, 2017) parsed using `csv.QUOTE_NONE` to eliminate multiline quote absorption.
  - Partitions: **Train: 10,269**, **Validation: 1,277**, **Official Test: 1,278**.
  - Documented duplicate collisions with training set removed (5 from test, 7 from validation).
- **Model Specification:**
  - Feature Extractor: `TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True)`.
  - Estimator: `LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000, class_weight='balanced', random_state=42)`.
- **Evaluation Baseline (`models/evaluation_metrics.json`):**
  - Accuracy: `63.07%` (806 / 1278).
  - Macro Precision: `62.59%` | Macro Recall: `62.72%` | Macro F1: `0.6262`.
  - Confusion Matrix: $\begin{pmatrix} 333 & 221 \\ 251 & 473 \end{pmatrix}$.
- **Responsible AI Prediction Semantics:**
  - Classes: `"Higher-veracity linguistic pattern"` vs `"Lower-veracity linguistic pattern"`.
  - Uncertainty: Boundary margin check ($|P_1 - P_0| < 0.15$) automatically flags `"Uncertain / Insufficient Model Signal"`.
  - Explicit advisory: Informs analysts that scores represent stylistic and lexical alignment with the US political benchmark, not factual truth determinations.

### 3.4 Retrieval & Deduplication Tier
- **Fact-Check Retrieval (`src/retrieval/fact_check.py`):**
  - Indexes 8 authentic public cases in `data/fact_checks.json` (from PIB Fact Check, BOOM Live, Alt News).
  - Rank-BM25Plus ranking guarded by a mandatory lexical overlap check (`any(token in self.corpus_vocab for token in query_tokens)`), preventing floor score false-positives on out-of-vocabulary queries.
  - Transparent empty states rendered when no genuine matches exist.
- **Coverage Clustering (`src/processing/deduplication.py`):**
  - Cosine similarity matrix computed via TF-IDF character and word n-grams.
  - Categorizes relations into exact republishing ($\ge 0.90$), syndication ($\ge 0.70$), and similar coverage ($\ge 0.55$). Preserves all publisher names and source URLs.

### 3.5 Streamlit Presentation Tier (`src/ui/`)
- **Unified Navigation (`src/ui/navigation.py`):** Single session state bus synchronized with browser URL parameters (`?page=...&q=...`). Dynamic sidebar reporting real datastore totals, indexed fact-check counts, and live last ingestion timestamps.
- **Screen 1 (Overview Dashboard):** Live metric cards computed directly from `db.get_article_count()`, `service.get_source_statuses()`, and `service.analyze_coverage_clusters()`.
- **Screen 2 (News Monitor):** Dynamic publisher filtering from active database records, parameterized search, true pagination counting (`Showing 1 - 50 of 819 records`), and safe HTML escaping.
- **Screen 3 (Analyze Article):** Real-time latency measurement (`time.perf_counter()`), actual non-zero feature coefficient extraction (`get_influential_tokens`), live related cluster matching, and honest empty states.
- **Screen 4 (Evidence & Coverage):** Pure data binding to `selected_article_for_evidence` or latest stored story. Purged all wireframe mockups.
- **Screen 5 (Methodology & Sources):** Accurate specification reflecting 10,000 vocab, L-BFGS solver, synchronous pipeline execution, and exact LIAR evaluation metrics.

---

## 4. Verification Suite & Quality Gates

All automated verification commands were executed in the project virtual environment (`.venv`, Python 3.12.10):

| Verification Gate | Command Executed | Observed Result | Status |
| :--- | :--- | :--- | :--- |
| **Bytecode Compilation** | `.venv\Scripts\python.exe -m compileall -q src tests app.py` | 0 errors | **PASS** |
| **Package Consistency** | `.venv\Scripts\python.exe -m pip check` | No broken requirements found | **PASS** |
| **Linting** | `.venv\Scripts\python.exe -m ruff check src tests app.py` | All checks passed! (0 errors) | **PASS** |
| **Formatting** | `.venv\Scripts\python.exe -m ruff format --check src tests app.py` | 28 files already formatted | **PASS** |
| **Automated Tests** | `.venv\Scripts\python.exe -m pytest -v` | **54 passed in 5.03s** | **PASS** |
| **Security Audit** | `.venv\Scripts\python.exe -m bandit -r src app.py -ll` | 0 High, 0 Medium issues | **PASS** |

### Breakdown of Passing Tests (54 Total):
- `tests/test_all.py` (18 tests): Cleaner, tokenizer, canonical URL normalizer, ML inference, GDELT normalization and retry, RSS parsing and timeout handling, BM25 retrieval and zero-overlap guard, deduplication, SQLite persistence, and news service contract.
- `tests/test_backend_phase2.py` (17 tests): GDELT rate limits and timeouts, RSS 5MB limits and redirect safety, provider failure isolation, idempotent upserts, literal wildcard searches, pagination, transaction rollback.
- `tests/test_ml_phase4.py` (11 tests): TSV quote parsing, label mapping, duplicate exclusion accounting, artifact compatibility, missing artifact handling, linguistic label semantics, boundary uncertainty detection, confusion matrix consistency, fact-check provenance, deduplication thresholds and clustering.
- `tests/test_ui.py` (8 tests): AppTest initial load, full 5-page navigation, article screening interaction, URL query parameter deep linking, default News Monitor record rendering, Evidence & Coverage live rendering, Methodology verified specs.

---

## 5. Live External Provider Verification

Live network smoke tests were conducted against configured endpoints:
- **National RSS Feeds:**
  - *The Times of India (National):* HTTP 200 (653ms, 22.8 KB) — **OPERATIONAL**
  - *The Hindu (National):* HTTP 200 (588ms, 45.5 KB) — **OPERATIONAL**
  - *NDTV (India News):* HTTP 200 (2223ms, 28.8 KB) — **OPERATIONAL**
  - *Indian Express (India):* HTTP 200 (446ms, 213.3 KB) — **OPERATIONAL**
  - *Hindustan Times (India):* HTTP 200 (410ms, 98.2 KB) — **OPERATIONAL**
  - *Livemint (National & Economy):* HTTP 200 (414ms, 37.9 KB) — **OPERATIONAL**
- **GDELT 2.0 Document API:**
  - Live query encountered upstream HTTP 429 Rate Limiting from GDELT servers.
  - The application cleanly absorbed the rate limit, logged the backoff notification, safely recorded provider status, and preserved all existing database records without crashing.

---

## 6. Clean Checkout & Security Audit

1. **Local Demonstration Binding:** Streamlit is configured for local deployment (`127.0.0.1`), preventing accidental public exposure.
2. **Credential Safety:** Zero API keys, passwords, or personal credentials exist in source code or committed artifacts.
3. **Injection Prevention:** All SQLite queries use parameter binding (`?`); search inputs escape literal LIKE metacharacters.
4. **Input Sanitization:** All article headlines, summaries, and URLs rendered into HTML containers are strictly escaped using `html.escape()`.
5. **Clean Checkout Reproducibility:**
   - Canonical TSV dataset files are preserved under `data/liar/`.
   - Serialized ML artifacts (`models/tfidf_vectorizer.joblib`, `models/classifier.joblib`) are present and verified.
   - Missing model artifacts trigger honest unavailable messages rather than unhandled exceptions or synthetic data generation.

---

## 7. Remaining Known Limitations (Transparently Documented)

1. **Benchmark Domain Shift:** The ML model is trained on US political statements (LIAR corpus). It provides linguistic framing heuristics and must never be interpreted as an automated arbiter of real-world Indian news events.
2. **Fact-Check Corpus Scale:** The indexed fact-check repository contains 8 curated public records for demonstration and retrieval verification; it is not currently connected to an automated live web crawler.
3. **GDELT Upstream Throttling:** GDELT DOC API frequently enforces global IP rate limits (HTTP 429); the platform gracefully tolerates this via exponential backoff and cached SQLite fallback.

---

## 8. Final Acceptance Declaration

NewsLens India satisfies all functional, architectural, security, and responsible AI acceptance criteria. Every displayed metric, status, and claim is grounded in verified code and datastore state.

**Project Status: READY FOR DEMONSTRATION**
