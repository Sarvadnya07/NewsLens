# NewsLens India — Master Documentation Conflict Log & Reconciliation Matrix

**Document Purpose:** Complete forensic log of all factual, architectural, metric, and tooling discrepancies identified across historical project documentation and their definitive reconciliation against authoritative code, configurations, and evaluation artifacts.  
**Audit Date:** October 31, 2026 (Refined Academic Edition v2.0.0)  
**Auditor / Architect:** Senior Academic Technical Writer, Documentation Architect & ML Researcher  
**Governing Standard:** Documentation Kernel (Strict Source-of-Truth Hierarchy & Preservation-First Rule)  

---

## 1. Discrepancy & Resolution Summary Table

| Conflict ID | Domain | Historical Stated Value | Canonical / Current Stated Value | Source of Truth | Definitive Resolution & Action Taken |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DISC-01** | **ML Dataset Partition Counts** | Train: 10,240 \| Valid: 2,571 / 1,277 \| Test: 2,551 / 1,262 | Canonical TSV: Train: **10,269**, Valid: **1,284**, Test: **1,283**. Evaluated Subset: Train: **10,269**, Valid: **1,277** (7 leaks removed), Official Test: **1,278** (5 leaks removed). | `research/fake-news-detection/liar_dataset/` TSVs & `docs/LIAR_PROVENANCE_RECONCILIATION.md` | Discovered that raw TSVs contained unclosed double quotes inside statements. Standard Pandas `read_csv` absorbed 29 train records and 16 test records into multiline strings. Fixed in `src/ml/train.py` via `csv.QUOTE_NONE`. Historical 10,240 and 1,262 metrics documented as milestone results. |
| **DISC-02** | **ML Test Evaluation Metrics** | Accuracy: `61.80%` (0.617959) or `62.36%` (0.623613). Macro-F1: `0.6158` or `0.6194`. | Accuracy: **`63.07%`** (0.630673). Macro-F1: **`0.6262`** (0.626187). Weighted-F1: **`0.6316`** (0.631634). | `models/evaluation_metrics.json` | The canonical model trained on all 10,269 canonical train rows and evaluated on 1,278 official test rows achieved 63.07% accuracy. Older metrics reflected either the combined validation+test subset (2,539 rows) or the quote-absorbed test subset (1,262 rows). Reconciled in all primary docs. |
| **DISC-03** | **Confusion Matrix Values** | Older matrix: `[[327, 224], [251, 460]]` ($N=1,262$) or combined `[[662, 452], [518, 907]]` ($N=2,539$). | Canonical matrix: **`[[333, 221], [251, 473]]`** ($N=1,278$). | `models/evaluation_metrics.json` | Exact agreement confirmed: $333 + 221 + 251 + 473 = 1,278$ samples. Accuracy: $(333+473)/1278 = 806/1278 = 63.0673\%$. |
| **DISC-04** | **Automated Test Count** | Documented as 13, 20, or 23 tests across historical reports. | **26 Automated Tests** (21 in `tests/test_all.py`, 5 in `tests/test_ui.py`). All 26 pass in 3.71s. | `pytest` test suite execution | Test suite grew incrementally: 13 baseline -> 20 after hardening -> 23 after GDELT retry and BM25 zero-overlap tests -> 26 after adding 3 canonical TSV schema, quote absorption, and leakage isolation tests. |
| **DISC-05** | **Configured RSS Feed Sources** | Earlier reports listed *Deccan Herald* (`https://www.deccanherald.com/rss/national.rss`). | *Livemint (National & Economy)* (`https://www.livemint.com/rss/news`). | `src/ingestion/rss.py` | Deccan Herald deprecated their RSS endpoint, returning HTTP 404. In `ENGINEERING_AUDIT.md`, Deccan Herald was replaced with Livemint, restoring 100% feed health across all 6 national publishers. |
| **DISC-06** | **GDELT Operational Reality** | Conceptual docs describe GDELT as continuously streaming real-time news. | GDELT 2.0 Doc API is functional but rate-limited (5s cooldown) and subject to transient HTTP 429 throttling / SSL timeouts. | `src/ingestion/gdelt.py` & live audit logs | GDELT is integrated defensively with 15s timeout, 1-attempt transient retry, and 5s cooldown, returning an empty list gracefully on 429 rather than crashing. Mocked tests verify schema parsing. Live operation requires respecting rate limits. |
| **DISC-07** | **Scikit-Learn Version Compatibility** | Global Python 3.13 had scikit-learn 1.7.2, triggering `InconsistentVersionWarning` or `AttributeError` on `multi_class`. | Project-local virtual environment `.venv` uses **Python 3.12.10** and **scikit-learn 1.9.1**. | `.venv\Scripts\python.exe` & `models/evaluation_metrics.json` | The model artifacts were serialized under scikit-learn 1.9.1. When executed in `.venv`, models unpickle with 0 warnings and tests pass 100%. Master document mandates running under `.venv`. |
| **DISC-08** | **Article Storage Count** | Older reports documented 435 or 487 articles in SQLite database. | **666 verified articles** stored in `data/newslens.db`. | `data/newslens.db` SQL query | The database holds 666 articles across 6 publishers (Indian Express: 400, Hindustan Times: 107, The Hindu: 63, NDTV: 40, Livemint: 35, TOI: 21) with 0 duplicate URLs. |
| **DISC-09** | **Fact-Check Corpus Size** | Some planning documents envisioned hundreds of crawled fact-checks. | **8 verified seed claims** from accredited Indian watchdogs (PIB Fact Check, BOOM Live, Alt News) in `data/fact_checks.json`. | `data/fact_checks.json` | Current implementation indexes 8 authentic high-veracity reference claims for BM25Plus demonstration. Expansion to dynamic scraping is cataloged under Future Scope (Ch. 7). |
| **DISC-10** | **BM25Plus Zero-Overlap Scoring** | Standard BM25Plus assigns a lower-bound delta score ($\delta > 0$) even when query terms have zero match with corpus. | Hardened with pre-retrieval lexical token overlap check (`self.corpus_vocab`). | `src/retrieval/fact_check.py` | Without the guard, queries like `"quantum astrophysics"` received scores of 2.19 - 4.22 and passed `min_score=1.0`. With the guard, zero-overlap queries immediately return `[]`. |

---

## 2. Unresolved / Open Information Gaps

1. **Academic Affiliation / Author Metadata:**
   - Git commits reference `Sarvadnya07 <sarvadnyasonkambale0@gmail.com>`.
   - Specific college, department, university, guide name, and semester details are not present in workspace files.
   - *Resolution:* Front matter includes clean academic structure with maintainer details preserved, without fabricating unverified institutional names or registration IDs.
2. **Dynamic Fact-Check Web Crawling:**
   - The current system loads fact-checks from local JSON (`data/fact_checks.json`). Automated periodic web scrapers for PIB/BOOM/AltNews are not implemented in `src/`.
   - *Resolution:* Correctly classified as an implemented static seed catalog with automated dynamic scraping documented under Future Scope (Ch. 7).
