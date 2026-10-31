# NewsLens India — Final Comprehensive Repository Pruning Report

## 1. Executive Summary

This report establishes the definitive technical and architectural baseline of the **NewsLens India** codebase following aggressive second-pass pruning and technology-stack simplification.

The goal of this operation was to eliminate all genuinely unnecessary, obsolete, external, duplicated, or orphaned files, libraries, and language toolchains while preserving 100% of the required system capabilities, research provenance, canonical datasets, models, and tests.

---

## 2. Quantitative Pruning & Repository Metrics

| Metric | Before Second-Pass Pruning | After Second-Pass Pruning | Absolute Reduction |
|---|---|---|---|
| **Total Non-Venv Files** | 2,840 files | **60 files** | **-2,780 files (-97.9%)** |
| **Total Non-Venv Repository Size** | 36,230,882 bytes (36.2 MB) | **4,855,124 bytes (4.8 MB)** | **-31.38 MB (-86.6%)** |
| **Research Cloned Files** | 2,575 files | **1 provenance summary** | **-2,574 files (-99.9%)** |
| **Design Prototype Files** | 11 files (4.89 MB) | **0 (DESIGN_SPEC preserved)** | **-11 files (-100%)** |
| **Direct Runtime Dependencies** | 10 packages | **8 packages** | **-2 dev tools separated** |
| **Development Dependencies** | 0 (bundled in requirements.txt) | **3 packages (requirements-dev.txt)** | Cleanly decoupled |
| **Active Python Source Files** | 20 modules (including app.py) | **20 modules** | Preserved & verified |
| **Automated Tests** | 26 tests (21 unit + 5 UI) | **26 tests (21 unit + 5 UI)** | **100% Passing (0 failures)** |

---

## 3. Major Pruning Actions Executed

### 3.1 Aggressive Research Repository Pruning
- **Previous State:** The repository contained four Git submodules (`research/fake-news-detection`, `research/feedparser`, `research/gdelt-doc-api`, `research/rank_bm25`) totaling 2,575 files and 27.9 MB of upstream source code, documentation, benchmarks, and tests that were never imported by application runtime.
- **Actions Executed:**
  1. Extracted and validated canonical LIAR benchmark dataset splits (`train.tsv`, `valid.tsv`, `test.tsv`, `README`, `LICENSE`) to first-party directory `data/liar/`.
  2. Verified exact SHA-256 hashes against original provenance.
  3. Created `data/liar/PROVENANCE.md` documenting schema, licensing, and Wang (ACL 2017) citation.
  4. Updated `src/ml/train.py` and `tests/test_all.py` to reference `data/liar/`.
  5. Backed up all submodules externally at `..\NewsLens-India-Backup-Pass2\research\`.
  6. Removed git submodule tracking via `git rm --cached` and deleted `.gitmodules`.
  7. Deleted all cloned submodule files from working tree.
  8. Created `research/PROVENANCE.md` recording upstream URLs, commits, and library roles.

### 3.2 Design Prototype & Asset Pruning
- **Previous State:** Tracked directory `stitch_newslens_india_platform/` contained 11 files (4.89 MB) consisting of duplicate HTML prototype renders and high-resolution PNG screen captures.
- **Actions Executed:**
  1. Backed up entire directory externally at `..\NewsLens-India-Backup-Pass2\stitch_newslens_india_platform\`.
  2. Preserved the textual UI specification `DESIGN.md` into `docs/design/DESIGN_SPECIFICATION.md`.
  3. Completely untracked and deleted `stitch_newslens_india_platform/` using `git rm -r`.

### 3.3 Dependency Decoupling (Runtime vs. Development)
- **Previous State:** `requirements.txt` mixed production runtime dependencies with development and testing tools (`pytest`, `ruff`).
- **Actions Executed:**
  1. Cleanly separated direct dependencies:
     - `requirements.txt`: 8 runtime dependencies (`streamlit`, `scikit-learn`, `pandas`, `numpy`, `feedparser`, `rank_bm25`, `requests`, `joblib`).
     - `requirements-dev.txt`: Development and security tooling referencing `-r requirements.txt` plus `pytest`, `ruff`, and `bandit`.
  2. Updated `.github/workflows/ci.yml` to install `requirements-dev.txt`.
  3. Verified environment with `pip check` (0 broken requirements).

### 3.4 Tooling and Cache Hygiene
- Corrected accidental MD5 regression in `src/services/news_service.py`, restoring hardened SHA-256 for manual article submission. Bandit SAST passes with 0 issues.
- Standardized `pyproject.toml` to `target-version = "py312"`.
- Cleaned all non-venv `__pycache__` directories and updated `.gitignore` to exclude `*.bak` and `models/backup/`.

---

## 4. Preservation of Core Capabilities

1. **GDELT News Ingestion (`src/ingestion/gdelt.py`):** Rate throttling (5s interval), bounded timeout (15s), retry handling.
2. **RSS Ingestion (`src/ingestion/rss.py`):** Monitored feeds from 6 major Indian publishers with per-feed error isolation.
3. **Canonical Normalization (`src/models.py`):** Canonical URL normalization and schema dataclasses.
4. **SQLite Persistence (`src/storage/database.py`):** WAL mode, parameterized queries, transaction context managers, busy timeout (5000ms).
5. **Misinformation Screening (`src/ml/predict.py`):** TF-IDF + Logistic Regression inference with safety fallbacks.
6. **Fact-Check Retrieval (`src/retrieval/fact_check.py`):** BM25Plus retrieval over indexed Indian fact-check claims with zero-overlap guardrail.
7. **Syndication Deduplication (`src/processing/deduplication.py`):** Pairwise cosine similarity matrix clustering.
8. **User Interface (`src/ui/`):** Streamlit 5-page diagnostic ledger matching the investigative design specification with honest telemetry.

---

## 5. Verification Results

- **Python Syntax Compilation:** Clean (`compileall` passed, exit code 0)
- **Dependency Tree:** Clean (`pip check` passed, 0 broken requirements)
- **Ruff Linter:** Clean (`All checks passed!`)
- **Ruff Formatter:** Clean (`23 files already formatted`)
- **Bandit SAST Security:** Clean (0 High, 0 Medium issues across 4,207 LOC)
- **Pytest Suite:** **26 passed in 4.16s** (100% pass rate)

---

## 6. Final Architecture Structure

```text
NewsLens-India/
├── .editorconfig
├── .gitattributes
├── .gitignore
├── app.py
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
├── pytest.ini
├── README.md
├── requirements-dev.txt
├── requirements-lock.txt
├── requirements.txt
├── SECURITY.md
├── THIRD_PARTY_NOTICES.md
│
├── .github/
│   ├── CODEOWNERS
│   ├── pull_request_template.md
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
│       ├── ci.yml
│       └── secrets.yml
│
├── data/
│   ├── fact_checks.json
│   ├── newslens.db
│   └── liar/
│       ├── train.tsv
│       ├── valid.tsv
│       ├── test.tsv
│       ├── README
│       ├── LICENSE
│       └── PROVENANCE.md
│
├── docs/
│   ├── codebase/
│   │   ├── FINAL_PRUNING_REPORT.md
│   │   └── PRUNING_CHANGELOG.md
│   ├── design/
│   │   └── DESIGN_SPECIFICATION.md
│   └── [historical reports]
│
├── models/
│   ├── classifier.joblib
│   ├── tfidf_vectorizer.joblib
│   └── evaluation_metrics.json
│
├── research/
│   └── PROVENANCE.md
│
├── src/
│   ├── models.py
│   ├── ingestion/
│   │   ├── gdelt.py
│   │   └── rss.py
│   ├── preprocessing/
│   │   └── cleaner.py
│   ├── ml/
│   │   ├── predict.py
│   │   └── train.py
│   ├── retrieval/
│   │   └── fact_check.py
│   ├── processing/
│   │   └── deduplication.py
│   ├── storage/
│   │   └── database.py
│   ├── services/
│   │   └── news_service.py
│   └── ui/
│       ├── __init__.py
│       ├── components.py
│       ├── navigation.py
│       ├── theme.py
│       └── pages/
│           ├── __init__.py
│           ├── dashboard.py
│           ├── news_monitor.py
│           ├── article_analysis.py
│           ├── evidence_coverage.py
│           └── methodology.py
│
└── tests/
    ├── test_all.py
    └── test_ui.py
```
