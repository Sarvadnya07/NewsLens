# Phase 4 Diagnostic Report: ML Pipeline, Fact-Check Retrieval, Evidence Provenance & Methodology Correction

**Project:** NewsLens India — Near-Real-Time Indian News Monitoring & Misinformation Screening  
**Module:** Phase 4 ML Pipeline, Fact-Check Retrieval, Evidence Provenance & Methodology Correction  
**Date:** October 31, 2026  
**Status:** COMPLETE & FULLY VERIFIED  

---

## 1. Executive Summary

Phase 4 completed an in-depth audit, technical correction, and responsible AI alignment across the Machine Learning inference and training pipeline, the BM25Plus fact-check retrieval engine, TF-IDF coverage clustering, and application-wide methodology documentation.

Key objectives achieved:
1. **Separation of Distinct Operations:** Enforced strict separation between **ML linguistic screening**, **local fact-check retrieval**, **multi-publisher similarity clustering**, and **factual truth determination**.
2. **Responsible Prediction Semantics:** Replaced all inaccurate categorical truth labels with technically honest, calibrated terminology (`"Higher-veracity linguistic pattern"`, `"Lower-veracity linguistic pattern"`, `"Uncertain / Insufficient Model Signal"`). Model outputs are explicitly identified as uncalibrated model class scores, with prominent domain-shift warnings regarding the US political statement benchmark (LIAR).
3. **Fact-Check Provenance Integrity:** Audited the local curated fact-check archive (8 authentic public cases from PIB Fact Check, BOOM Live, Alt News). Replaced mock/fabricated card rendering with transparent empty states and verified source links.
4. **Purged Unsupported Architectural Claims:** Completely removed unsupported buzzwords from user-facing screens and methodology documentation (e.g., claims of NER v4, OCR, gazette scrapers, social media ingestion, geocoding, 48,000 vocabulary, calibrated probability vectors, or background daemons).
5. **Rigorous Test Coverage:** Added 11 focused unit and integration tests in `tests/test_ml_phase4.py`, expanding automated test coverage to **54 passing tests** with 0 Ruff violations and verified database integrity at 819 articles.

---

## 2. Actual Machine Learning Configuration & Provenance

### 2.1 Dataset Provenance & Split Audit
The model is trained exclusively on the canonical LIAR benchmark dataset (Wang, 2017) using PolitiFact statements:
- **Source TSVs:** `data/liar/train.tsv` (10,269 raw rows), `data/liar/valid.tsv` (1,284 raw rows), `data/liar/test.tsv` (1,283 raw rows).
- **Parser:** Python `csv.reader` configured with `csv.QUOTE_NONE` to prevent standard RFC 4180 quote absorbers from erroneously collapsing multiline statements into single records.
- **Duplicate Leakage Elimination:**
  - 5 statement collisions purged from test set.
  - 7 statement collisions purged from validation set.
  - Final prepared partitions: **Train: 10,269**, **Validation: 1,277**, **Official Test: 1,278**.
- **Six-Class to Binary Label Mapping:**
  - `Class 0 (Lower-veracity)`: `pants-fire`, `false`, `barely-true` (554 test samples).
  - `Class 1 (Higher-veracity)`: `half-true`, `mostly-true`, `true` (724 test samples).
  - *Note:* Class 1 includes "half-true" statements and represents relative linguistic alignment, never absolute empirical truth.

### 2.2 Feature Pipeline & Estimator Parameters
- **Text Preprocessing:** NFKD unicode normalization, HTML tag removal, URL stripping, lowercase conversion, non-word punctuation stripping via `clean_text`.
- **Feature Extraction:** Scikit-Learn `TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True)`. Fitted strictly on `train_df["cleaned"]`.
- **Classifier:** Scikit-Learn `LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000, class_weight='balanced', random_state=42)`.
- **Artifacts on Disk:** Verified identical feature dimension ($10,000$) and class ordering ($[0, 1]$) in `models/tfidf_vectorizer.joblib` and `models/classifier.joblib`.

### 2.3 Empirical Evaluation Baseline (Single Source of Truth: `models/evaluation_metrics.json`)
Evaluated strictly on the untouched official test partition (1,278 samples):
- **Accuracy:** `63.07%` ($806 / 1278$)
- **Macro Precision:** `62.59%`
- **Macro Recall:** `62.72%`
- **Macro F1-Score:** `0.6262`
- **Weighted F1-Score:** `0.6316`
- **Confusion Matrix:**
  $$\begin{pmatrix} 333 & 221 \\ 251 & 473 \end{pmatrix}$$
  - *Row 0 (Actual Lower-Veracity):* 333 True Negatives, 221 False Positives ($57.02\%$ Precision, $60.11\%$ Recall).
  - *Row 1 (Actual Higher-Veracity):* 473 True Positives, 251 False Negatives ($68.16\%$ Precision, $65.33\%$ Recall).

---

## 3. Retrieval & Deduplication Architecture

### 3.1 Local Fact-Check Retrieval (`src/retrieval/fact_check.py`)
- **Corpus:** 8 authentic public cases in `data/fact_checks.json` verified from PIB Fact Check (India), BOOM Live, and Alt News.
- **Algorithm:** `rank_bm25.BM25Plus` indexed over `claim + explanation + claimant`.
- **Lexical Overlap Guard:** Hard pre-scoring check `any(token in self.corpus_vocab for token in query_tokens)` prevents out-of-vocabulary queries from returning floor score false-positives.
- **Advisory:** Explicit metadata attached to all retrieved matches: `"A search match indicates similarity between the query and an investigated claim. It does not automatically verify that the queried article is identical."`

### 3.2 Coverage Clustering & Deduplication (`src/processing/deduplication.py`)
- **Clustering Engine:** TF-IDF word and sublinear n-gram $(1, 2)$ cosine similarity.
- **Threshold Tiers:**
  - $\ge 0.90$: `"exact_or_republished"`
  - $\ge 0.70$: `"likely_syndicated"`
  - $\ge 0.55$: `"similar_coverage"`
  - $< 0.55$: `"unrelated"`
- **Source Attribution:** Retains all publisher names and original canonicalized URLs.

---

## 4. Remediation of Terminology & Unsupported Claims

| Previous Claim / Term | Audited Status | Corrected Implementation / Terminology |
| :--- | :--- | :--- |
| `"Calibrated Probability Vector"` | Unsupported | **"Model Class Score (Uncalibrated)"** |
| `"48,000 Vocab Max / 3-grams"` | Inaccurate | **"10,000 Vocab Max / (1, 2) n-grams"** |
| `"Logit (L2 Solver: SAGA)"` | Inaccurate | **"Logistic Regression (L-BFGS)"** |
| `"Live Microservice / Batch Sync"` | Unsupported | **"Synchronous Module / Local Data Store"** |
| `"IFCN Signatory Registry Sync: Live"` | Unsupported | **"Local Archive Retrieval (8 Curated Cases)"** |
| `"Verified True / Confirmed Misleading"` | Epistemically False | **"Higher-veracity / Lower-veracity linguistic pattern"** |
| Fabricated fallback fact-check cards | Mock wireframe | **Honest `render_empty_state()`** |
| Indic script normalization / NER v4 / OCR | Unsupported | Purged from all UI descriptions and code |

---

## 5. Verification Suite & Quality Assurance

Execution in `.venv` (Python 3.12.10):
1. **Automated Tests:** `pytest -v` $\to$ **54 passed in 5.72s**.
   - 18 core tests in `tests/test_all.py`
   - 17 backend tests in `tests/test_backend_phase2.py`
   - 11 ML & retrieval tests in `tests/test_ml_phase4.py`
   - 8 UI integration tests in `tests/test_ui.py`
2. **Linting:** `ruff check src tests` $\to$ **All checks passed!** (0 errors).
3. **Formatting:** `ruff format --check src tests` $\to$ **27 files already formatted**.
4. **Bytecode Compilation:** `python -m compileall src tests` $\to$ **0 errors**.
5. **Database Integrity:** Verified `data/newslens.db` remains pristine with **819 articles** and **7 source status records**.
