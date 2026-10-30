# Engineering Audit & Hardening Log

**Date of Audit:** October 30, 2026  
**Auditor:** Principal Software Architect, Senior Python Engineer & QA Lead  
**Scope:** Comprehensive verification, defect resolution, and production-quality hardening of NewsLens India.

---

## 1. Initial State & Baseline Inspection

- **Git Branch:** `hardening-audit` created from baseline commit `9511b24`.
- **Environment:** Windows, Python 3.13.9, pip 26.2.1, ruff 0.16.3, pytest 9.1.1.
- **Initial Verification Status:**
  - `python -m compileall -q .`: Passed with 0 syntax errors.
  - Initial tests: 13 tests passed, but generated 10 deprecation warnings from `joblib` array shape setting in NumPy 2.5+.
  - Ruff linting: 53 lint/import formatting errors across application and tests.

---

## 2. Prioritized Defect Log & Resolutions

### Defect 1 (P0): Deccan Herald RSS Feed 404 Outage
- **Symptom:** `https://www.deccanherald.com/rss/national.rss` returned HTTP 404, causing Deccan Herald to fail on every feed refresh.
- **Root Cause:** Upstream Deccan Herald restructured their CMS endpoints, deprecating the legacy RSS URL.
- **Fix:** Audited active Indian national feeds. Replaced unavailable Deccan Herald with *Livemint (National & Economy)* (`https://www.livemint.com/rss/news`), returning 35 fresh stories with HTTP 200. Verified all 6 configured feeds now operate at 100% success rate (435 live stories ingested).

### Defect 2 (P0): LIAR Benchmark Validation Split Origin & Leakage Documentation
- **Symptom:** Discrepancy between standard LIAR test subset count (1,267 rows) and research `test.csv` (2,551 rows).
- **Root Cause:** The author of `research/fake-news-detection` concatenated `valid.tsv` (1,284) and `test.tsv` (1,267) to create `test.csv` (2,551). In addition, 12 statement strings overlapped with the training set.
- **Fix:** Documented the exact split composition in `docs/DATASET_AUDIT.md`. Hardened `src/ml/train.py` to systematically audit and drop duplicate statement collisions prior to vectorization, ensuring a clean 2,539-record held-out test split.

### Defect 3 (P1): Deprecation Warnings on NumPy 2.5 / Python 3.13
- **Symptom:** 10 `DeprecationWarning: Setting the shape on a NumPy array has been deprecated in NumPy 2.5` warnings during test runs and model loading.
- **Root Cause:** Joblib's internal array unpickling path invokes deprecated numpy shape assignment in NumPy 2.x.
- **Fix:** Wrapped model artifact deserialization in `src/ml/predict.py` with scoped warning filters (`warnings.catch_warnings()`), resulting in a clean test execution log (0 warnings).

### Defect 4 (P1): Missing URL Canonicalization in News Pipeline
- **Symptom:** Articles with identical content could be saved under multiple URLs due to tracking query strings (`?utm_source=...`, `?utm_medium=...`, `#publisher=...`).
- **Root Cause:** Ingestion directly hashed the raw URL string.
- **Fix:** Implemented `canonicalize_url()` in `src/models.py`. Stripped UTM parameters, tracking flags, and duplicate fragments across GDELT, RSS, and manual submission pipelines.

### Defect 5 (P1): Deduplication Categorization
- **Symptom:** Cosine similarity lumped all matching articles as "related" without categorizing exact vs syndicated duplicates.
- **Root Cause:** Binary thresholding without relationship grading.
- **Fix:** Implemented `classify_relationship()` in `src/processing/deduplication.py`, distinguishing `exact_or_republished` (>= 0.90), `likely_syndicated` (>= 0.70), and `similar_coverage` (>= 0.55).

### Defect 6 (P1): HTML Injection Risk in News Dashboard
- **Symptom:** Untrusted external article titles and publisher strings rendered in Streamlit markdown could allow Markdown/HTML tag breakout.
- **Root Cause:** Unescaped strings in Markdown containers.
- **Fix:** Applied `html.escape()` across article titles, publishers, and claim text in `app.py`.

### Defect 7 (P2): Code Quality and Formatting
- **Symptom:** 53 ruff linting errors and unformatted files.
- **Fix:** Created `pyproject.toml` scoping Ruff to project source directories, organized import blocks, eliminated trailing whitespace, and formatted all files with `ruff format .`.
