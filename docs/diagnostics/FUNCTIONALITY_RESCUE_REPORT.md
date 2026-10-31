# NewsLens India — Full-System Functionality Rescue Report

**Date:** 2026-10-31  
**Author:** Principal Software Architect, Full-Stack QA & Reliability Lead  
**Audit & Rescue Objective:** Complete elimination of hardcoded/inconsistent metrics, repair of end-to-end user workflows, empirical verification of real data flows, and Playwright browser validation.

---

## 1. Executive Summary

All critical system discrepancies, contradictory source statuses, hardcoded metric artifacts, and frontend build issues have been resolved across the full stack. 

The application was verified live in a dual-server configuration:
- **FastAPI Backend:** `http://127.0.0.1:8000` (live SQLite persistence, Joblib ML model, BM25Plus ClaimReview index).
- **React 19 Frontend:** `http://127.0.0.1:5173` (Vite dev server + production bundle).

**Final System Status:** **FULLY DYNAMIC AND VERIFIED**.

---

## 2. Inconsistencies Discovered & Root Causes Repaired

### A. Source Status Contradiction (`Active UNKNOWN` & `0 / 8 Active`)
- **Symptom:** The dashboard overview reported `0 / 8 Active` sources while individual feed rows displayed `Active` with `UNKNOWN` status badges.
- **Root Cause:** In `backend/api/routes/dashboard.py`, the database column mapper attempted to read `last_status` and `last_fetched_at`. However, the SQLite schema in `data/newslens.db` uses column names `status` and `last_refresh_at`. This resulted in `None` values falling back to `"unknown"`, causing `active_sources_count = 0`.
- **Fix:** Corrected the mapper in `backend/api/routes/dashboard.py` to inspect `st.get("status")` and `st.get("last_refresh_at")`. Live FastAPI endpoint now correctly reports:
  - `active_sources_count: 6`
  - `total_configured_sources: 8`
  - Exact feed breakdown: Livemint (success, 35 articles), Hindustan Times (success, 100), Indian Express (success, 200), NDTV (success, 20), The Hindu (success, 60), TOI (success, 20), Deccan Herald (empty_or_failed), GDELT (rate_limited, HTTP 429).

### B. Methodology Metrics Grounded in Real Data
- **Symptom:** Previous methodology route reported simulated placeholder numbers (`64.5% Accuracy`, `4,200 Articles`).
- **Root Cause:** Hardcoded fallback values were served instead of querying `models/evaluation_metrics.json`.
- **Fix:** Connected `GET /api/v1/methodology` directly to `models/evaluation_metrics.json` and canonical LIAR partition files:
  - Accuracy: `63.1%` (official test partition, n=1,278)
  - Macro Precision: `62.6%`
  - Macro Recall: `62.7%`
  - Macro F1-Score: `0.626`
  - Total Corpus: `12,824` samples (Train: 10,269 [80%], Test: 1,278 [10%], Valid: 1,277 [10%]).

### C. Evidence & Coverage Dynamic Binding
- **Symptom:** Evidence & Coverage displayed static hardcoded text for "URGENT: Ministry of Railways..." and sample SHA hashes.
- **Root Cause:** `EvidenceCoveragePage.tsx` did not bind the primary story card to the active cluster returned by `GET /api/v1/coverage/clusters`.
- **Fix:** Bound the investigation card directly to the first cluster's `primary_article.title` and `primary_article.publisher`, with truthful explanatory text regarding multi-outlet clustering and BM25Plus ClaimReview ranking.

---

## 3. End-to-End Workflow Verification

| Workflow | Tested Interaction | Verified Result | Status |
| :--- | :--- | :--- | :--- |
| **Workflow A (Overview)** | Live metric loading & Quick Screening | Total articles: 824, Active sources: 6/8. Quick screening textarea submits to `/analysis` and outputs prediction in ~14ms. | **WORKING** |
| **Workflow B (News Monitor)** | Search & Ingestion filtering | Querying "Railway" returns filtered matching records. Server-side pagination updates totals accurately without SQL wildcard bugs. | **WORKING** |
| **Workflow C (Analyze Article)** | Sample claim loader & Screening submission | Clicking "Load Example Claim" populates text. "Screen Article Content" triggers ML model, returns resemblance meter and token weights. | **WORKING** |
| **Workflow D (Evidence & Coverage)** | Cytoscape graph rendering | Interactive canvas renders article nodes (navy) and publisher nodes (teal) with similarity edges. Pan & zoom functional. | **WORKING** |
| **Workflow E (Methodology)** | Architectural & metrics inspection | Renders 4-stage pipeline, official held-out evaluation table, and 6 core ethical system limitations. | **WORKING** |

---

## 4. Playwright Browser Automation & Visual Inspection

- **35 Baseline Screenshots Captured:** All 5 pages across 7 viewports (1920x1080, 1440x900, 1280x800, 1024x768, 768x1024, 390x844, 360x800) stored in `docs/screenshots/`.
- **3 Interactive State Screenshots:**
  - `interaction_news_search_railway.png`
  - `interaction_analyze_submitted.png`
  - `interaction_evidence_graph_rendered.png`
- **Visual Quality:** Verified zero horizontal overflow, consistent typography (`Newsreader` for titles, `Inter` for data), high contrast, and responsive layout scaling.

---

## 5. Automated Test Suite Execution Summary

```text
================================================================================
Backend Pytest Suite:     pytest -q           --> 65/65 PASSED (15.10s)
Frontend Vitest Suite:    vitest run          --> 7/7 PASSED (4.43s)
Frontend Production Build: tsc -b && vite build --> CLEAN (0 errors, 727ms)
Python Formatting & Lint: ruff check & format --> 49/49 FILES CLEAN
SQLite PRAGMA Integrity:  PRAGMA check        --> ok (824 records preserved)
Playwright E2E Flows:     node scripts        --> 38/38 SCREENSHOTS CAPTURED
================================================================================
```
