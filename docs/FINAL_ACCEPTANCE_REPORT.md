# NewsLens India — Final Acceptance Report and Demonstration Readiness Audit

**Audit Date:** October 30, 2026  
**Auditor:** Principal Software Architect, Senior ML Engineer & QA Lead  
**Repository Workspace:** `C:\Users\ASUS\Desktop\NewsLens-India`  
**Execution Environment:** Python 3.12.10 (`.venv\Scripts\python.exe`) on Windows 11  
**Verification Protocol:** Independent empirical validation across Git status, automated checks, ML artifacts, BM25 retrieval, live ingestion endpoints, SQLite persistence, and multi-page Streamlit UI automation.

---

## 1. Executive Status & Final Audit Verdict

**FINAL STATUS:** **Ready with documented limitations**

### Summary of Acceptance Audit:
- **Git Repository Hygiene:** Verified. No credentials, secret keys, temporary cache dumps, or uncommitted files entered the repository. All tracked changes are intentional hardening improvements.
- **Automated Verification Pipeline:** 100% PASS. `compileall` (0 syntax errors), `pip check` (0 broken requirements), `ruff check` (0 errors), `ruff format --check` (23 files cleanly formatted), and `pytest -v` (**23/23 tests passed, 0 warnings**).
- **ML Artifacts & Evaluation:** Verified. Vectorizer and classifier were retrained under active scikit-learn 1.9.1 in Python 3.12 without version mismatch warnings. Test accuracy (`61.80%`) and confusion matrix strictly agree. Prominent dataset limitations and domain shift disclosures are enforced.
- **BM25 Retrieval:** Verified. Out-of-vocabulary protection prevents zero-overlap false matches. Legitimate queries retrieve accredited fact checks (`pib_001`). Common-words-only queries correctly return empty results.
- **Live GDELT Ingestion:** Verified with documented limitation. Public GDELT API (`api.gdeltproject.org`) enforces strict 5-second IP throttling and returned HTTP 429 during live smoke testing. Handled fail-safe without crashing. Retry mechanism verified via unit tests.
- **Live Indian RSS Ingestion:** Verified. All 6 configured national and business feeds returned HTTP 200 and parsed valid breaking news entries (total 434 active entries across feeds).
- **SQLite Database Persistence:** Verified. 666 normalized articles across 6 publishers with 0 exact duplicates and 0 missing URLs or publisher names.
- **Streamlit Frontend:** Verified. All 5 pages render cleanly via headless `AppTest` without exceptions, and the live Streamlit daemon responds with HTTP 200 at `http://localhost:8501`.

---

## 2. Git State & Repository Hygiene

### Git Status & Diff Check
- `git diff --check`: **0 errors** (all trailing whitespace and EOF blank lines resolved).
- `git status --short`: Only expected, modified implementation files and verified local virtual environment `.venv`.
- **Repository Safety Audit:**
  - No API tokens, passwords, or secrets exist in tracked files.
  - No raw external repository contents from `research/` were committed to the main codebase.
  - Data directory contains only local SQLite database (`data/newslens.db`) and verified fact-check seeds (`data/fact_checks.json`).

### Changed Files & Rationale

| File | Change Scope | Rationale |
| :--- | :--- | :--- |
| `src/retrieval/fact_check.py` | Added `corpus_vocab` set and pre-scoring token overlap guard | Eliminates Okapi BM25Plus floor artifact where out-of-vocabulary queries returned low-scoring false matches. |
| `src/ingestion/gdelt.py` | Extended timeout to 15s; added 1-attempt transient retry with backoff | Hardens against transient network hiccups and SSL timeouts on public GDELT endpoints. |
| `models/` artifacts | Retrained `tfidf_vectorizer.joblib` and `classifier.joblib` under active venv | Eliminates `InconsistentVersionWarning` caused by scikit-learn version mismatch (1.7.2 vs 1.9.1). |
| `tests/test_all.py` | Added transient retry and zero-overlap regression tests | Validates GDELT retry logic and ensures BM25 vocabulary guard operates as intended. |
| `app.py` & `src/ui/` | Applied Ruff formatting and cleaned unused imports | Adheres to strict PEP 8 and Ruff code quality standards. |
| Documentation | Updated `TEST_REPORT.md`, `ML_EVALUATION_REPORT.md`, `IMPLEMENTATION_STATUS.md` | Synchronized test metrics and operational limitations. |

---

## 3. Automated Verification Checks

Executed using `.venv\Scripts\python.exe`:

| Command | Exit Code | Output / Evidence | Status |
| :--- | :---: | :--- | :--- |
| `python -m compileall -q src tests app.py` | `0` | Zero syntax or compilation errors. | **Verified** |
| `python -m pip check` | `0` | `No broken requirements found.` | **Verified** |
| `python -m ruff check src tests app.py` | `0` | `All checks passed!` (0 lint violations) | **Verified** |
| `python -m ruff format --check src tests app.py` | `0` | `23 files already formatted` | **Verified** |
| `python -m pytest -v` | `0` | **23 passed in 3.94s, 0 warnings, 0 failed, 0 skipped** | **Verified** |

### Test Breakdown (23 Tests)
- `tests/test_all.py` (18 tests):
  - Text preprocessing (clean text basic, empty/none handling, tokenization)
  - URL canonicalization (UTM stripping, tracking param removal)
  - ML inference (loading, empty/short input handling, probability calibration)
  - GDELT ingestion (normalization, 429 rate limiting, network exception recovery, transient retry recovery)
  - RSS feed ingestion (mocked parsing, malformed feed recovery)
  - Fact-check retrieval (claim matching, empty corpus resilience, empty query handling, zero-overlap protection)
  - Deduplication (TF-IDF cosine similarity clustering)
  - SQLite persistence (upsert, query filtering, transactional rollback)
  - Orchestration service (manual submission, query retrieval)
- `tests/test_ui.py` (5 tests):
  - UI imports and component integrity
  - Headless `AppTest` initial load
  - Multi-page navigation across all 5 pages
  - Article screening submission and screening widget flow
  - URL query parameter state synchronization

---

## 4. Machine Learning Artifacts & Evaluation Audit

### Artifact Verification
- **Classifier Artifact:** `models/classifier.joblib` (80.8 KB)
- **Vectorizer Artifact:** `models/tfidf_vectorizer.joblib` (386.9 KB)
- **Evaluation Metrics Record:** `models/evaluation_metrics.json`
- **Environment:** Scikit-learn 1.9.1 / Python 3.12.10.
- **Model Loading:** Executed with `-W error` — loads cleanly with **0 warnings**.

### Performance Metrics On Held-Out Test Set (2,539 Statements)
- **Training Set:** 10,240 statements (LIAR benchmark)
- **Test Set:** 2,539 statements (strictly independent split, 12 train-test duplicate leaks purged)
- **Accuracy:** `61.80%` (0.617959)
- **Macro Precision:** `61.57%`
- **Macro Recall:** `61.60%`
- **Macro F1-Score:** `61.58%`
- **Weighted F1-Score:** `61.83%`

### Confusion Matrix Agreement
```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              689                     472
Actual True (1)               498                     880
```
- Total test samples: $689 + 472 + 498 + 880 = 2,539$.
- Calculated accuracy: $\frac{689 + 880}{2539} = \frac{1569}{2539} \approx 61.7959\%$. Exactly matches recorded metric.
- Label mapping: `0 = Fake / Misleading`, `1 = True / Credible`.
- Decision boundary margin check: Uncertainty flag triggered whenever $|P(\text{True}) - P(\text{Fake})| < 0.15$.
- Dataset disclosure: Every prediction context displays the explicit disclaimer that the model was trained on the LIAR benchmark and captures lexical cues, not ground-truth facts.

---

## 5. Okapi BM25Plus Retrieval Audit

Tested against authentic fact checks (`data/fact_checks.json`):

| Test Scenario | Query | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Relevant known claim** | `"students free laptop scheme"` | Top match `pib_001` | 3 matches, Top: `pib_001` | **Verified** |
| **Exact claim** | `"Free laptop distribution scheme announced for all students."` | Top match `pib_001` | 3 matches, Top: `pib_001` | **Verified** |
| **Relevant paraphrase** | `"Government giving laptops to college students under new program"` | Top match `pib_001` | 3 matches, Top: `pib_001` | **Verified** |
| **Unrelated vocabulary** | `"quantum astrophysics supercollider dark matter hadron"` | 0 matches (no false positives) | 0 matches (`[]`) | **Verified** |
| **Generic common words** | `"is the and of for on at in"` | 0 matches (filtered by cleaner) | 0 matches (`[]`) | **Verified** |
| **Empty query** | `""` or `"   "` | 0 matches | 0 matches (`[]`) | **Verified** |
| **Missing corpus file** | Query on non-existent corpus | Safe graceful empty list | 0 matches (`[]`) | **Verified** |
| **Single-document corpus** | Query matching single document | 1 match | 1 match (`single_01`) | **Verified** |
| **Single-doc unrelated** | Query not matching single document | 0 matches | 0 matches (`[]`) | **Verified** |

---

## 6. Ingestion Endpoints Live Audit

### Live GDELT 2.0 Ingestion
- **Endpoint:** `https://api.gdeltproject.org/api/v2/doc/doc`
- **Request Parameters:** `query="India" sourcecountry:IN sourcelang:English`, `mode=artlist`, `format=json`, `maxrecords=5`.
- **Live Smoke Test Result:** The public GDELT endpoint returned `HTTP 429 Rate Limited: Please limit requests to one every 5 seconds` during the test run.
- **Resilience Behavior:** The client caught the 429 status code, logged a warning, and returned an empty list (`[]`) without crashing or propagating exceptions to the UI.
- **Unit Test Coverage:** Fully verified with mocked 200, 429, and transient timeout retries (`test_gdelt_transient_retry_success`).

### Live Indian Publisher RSS Ingestion
Tested all 6 configured national and business feeds independently:

| Publisher Source | Feed URL | HTTP Status | Parsing Status | Live Entries | Latest Item Timestamp | Normalization |
| :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **The Times of India** | `.../-2128936835.cms` | 200 | SUCCESS | 19 | `2026-10-30T17:13:59+05:30` | 19 normalized |
| **The Hindu** | `.../national/feeder/default.rss` | 200 | SUCCESS | 60 | `Fri, 30 Oct 2026 17:52:36 +0530` | 60 normalized |
| **NDTV** | `.../ndtvnews-india-news` | 200 | SUCCESS | 20 | `Fri, 30 Oct 2026 17:55:23 +0530` | 20 normalized |
| **Indian Express** | `.../section/india/feed/` | 200 | SUCCESS | 200 | `Fri, 30 Oct 2026 11:54:39 +0000` | 200 normalized |
| **Hindustan Times** | `.../rssfeed.xml` | 200 | SUCCESS | 100 | `Fri, 30 Oct 2026 17:33:46 +0530` | 100 normalized |
| **Livemint** | `.../rss/news` | 200 | SUCCESS | 35 | `Fri, 30 Oct 2026 18:01:27 +0530` | 35 normalized |

**Overall RSS Status:** **100% operational** across all 6 publishers with 434 active feed items accessible.

---

## 7. SQLite Persistence & Database Integrity Audit

Inspected active production database `data/newslens.db`:
- **Total Stored Articles:** `666`
- **Unique Canonical URLs:** `666`
- **Exact Duplicate Count:** `0`
- **Missing Publisher Fields:** `0`
- **Missing URL Fields:** `0`
- **Earliest Publication Timestamp:** `2026-10-24T03:23:10+00:00`
- **Latest Publication Timestamp:** `Wed, 28 Oct 2026 23:50:50 +0000`
- **Earliest Ingestion Timestamp:** `2026-10-30T10:49:52.907650+00:00`
- **Latest Ingestion Timestamp:** `2026-10-30T11:20:21.061340+00:00`
- **Persistence Verification:** Connection closed and reopened — exactly 666 records verified.
- **Publisher Breakdown:**
  - Indian Express: 400
  - Hindustan Times: 107
  - The Hindu: 63
  - NDTV: 40
  - Livemint: 35
  - The Times of India: 21

---

## 8. Streamlit Frontend & Multi-Page Audit

### Automated AppTest Verification (`tests/test_ui.py`)
Tested via Streamlit `AppTest` harness across all 5 navigation routes:

| Page Route | Component Coverage | Result |
| :--- | :--- | :---: |
| **1. Overview Dashboard** | Metric cards, breaking wire ticker, live feed sample, screening drawer | **PASS** (0 exceptions) |
| **2. News Monitor** | Feed ledger, multi-filter dropdowns, sorting order, publisher badges | **PASS** (0 exceptions) |
| **3. Article Analysis** | Headline input, text submission, probability gauge, uncertainty advisory | **PASS** (0 exceptions) |
| **4. Evidence & Coverage** | Fact-check retrieval table, similarity clustering, related article expanders | **PASS** (0 exceptions) |
| **5. Methodology & Sources**| Pipeline documentation, data governance, ML limitations, architecture cards | **PASS** (0 exceptions) |

### Live Server Daemon
- **Health Check:** `GET http://localhost:8501/_stcore/health` returned HTTP **200 OK**.
- **Interactive UI:** Running on port 8501 (`task-391`).

---

## 9. Documented Limitations & Demonstration Guidelines

1. **Statistical ML Model vs. Truth Verification:**
   - The Logistic Regression model predicts linguistic and stylistic framing patterns learned from the LIAR benchmark.
   - It **does not verify real-world facts** or corroborate breaking events.
   - The UI explicitly highlights this distinction with an alert banner on every screening output.
2. **Domain Shift:**
   - The classifier was trained on English political discourse. Regional Indian context, terminology, and transliterated names may exhibit domain shift.
3. **GDELT Public Rate Limits:**
   - The public GDELT Doc API strictly enforces a 5-second interval between queries per client IP. Rapid polling in a live demonstration will trigger HTTP 429 throttling. The application handles this by returning an empty result set and logging an advisory rather than crashing.
4. **Fact-Check Corpus Scope:**
   - The indexed fact-check catalog contains authentic seed claims from accredited watchdogs (PIB Fact Check, BOOM Live, Alt News). Queries on breaking news outside this catalog will return an honest "No relevant fact-check found" state.

---

## 10. Demonstration Launch Instructions

To launch the verified application for a live demonstration:

```powershell
# 1. Activate the dedicated virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run the automated verification test suite
python -m pytest -v

# 3. Launch the NewsLens India Streamlit dashboard
streamlit run app.py
```

*The application dashboard will open in the browser at `http://localhost:8501`.*
