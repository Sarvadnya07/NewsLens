# NewsLens India — Verified Feature Matrix

| Feature | Expected Behavior | Actual Verified Behavior | Status | Root Cause of Previous Failure | Fix Applied | Verification Evidence |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| **Total Stored Articles** | Return actual count from SQLite database | Returns 824 articles matching `SELECT COUNT(*) FROM articles` | **WORKING** | None (Preserved data integrity) | Direct SQLite count mapping | Live API + Pytest |
| **Active Source Tracking** | Display active vs configured feed count | Reports 6 active / 8 configured feeds accurately | **WORKING** | Inverted column name mapping (`last_status` vs `status`) | Mapped to `status` and `last_refresh_at` in `dashboard.py` | Live TestClient + Dashboard UI |
| **Feed Ingestion Health** | Per-feed items fetched and HTTP status | Displays TOI, Hindu, HT, IE, NDTV, Livemint as success with fetched counts; GDELT as rate_limited | **WORKING** | Missing status fallback in API schema | Dynamic per-feed status cards bound to SQLite table | Live Browser + Playwright |
| **Quick Article Screening** | Evaluate submitted claim syntax via ML model | Runs TF-IDF + Logistic Regression inference in ~14ms, returns decision score & salient tokens | **WORKING** | None | Form submission bound to `POST /analysis` | Live UI + Pytest |
| **News Monitor Search** | Keyword search across headlines with pagination | Parameterized SQL search executes with server pagination | **WORKING** | Historical wildcard escaping defect | Clean parameterized query with URL param sync | Pytest + Playwright interaction |
| **Source Type Filter** | Filter by RSS, GDELT, Manual, or All | Select dropdown updates query params and filters list | **WORKING** | None | Bound to `query_monitor_articles` service | Pytest `test_backend_phase2.py` |
| **Analyze Article Workbench** | In-depth 2x2 diagnostic grid with ClaimReview matches | Renders ML score meter, salient tokens, related coverage, and published fact-checks | **WORKING** | None | One-click example loader + TanStack mutation | Vitest + Playwright screenshot |
| **Evidence & Coverage Graph** | Interactive Cytoscape network graph | Renders article nodes (navy) and publisher nodes (teal) with similarity edges | **WORKING** | Static text passage in UI | Bound to dynamic clusters from `/coverage/clusters` | Playwright `canvas` inspection |
| **Methodology Metrics** | Empirical evaluation figures from model training | Accuracy: 63.1%, Macro Prec: 62.6%, Recall: 62.7%, F1: 0.626 across 1,278 test samples | **WORKING** | Hardcoded fallback values in route | Bound directly to `evaluation_metrics.json` | Live API + Vitest test |
| **Dataset Corpus Breakdown** | True split across training, test, and validation | Train: 10,269 (80%), Test: 1,278 (10%), Valid: 1,277 (10%) | **WORKING** | Hardcoded 4,200 sample simulator | Bound to canonical LIAR corpus counts | Live API + Vitest test |
| **Feed Refresh Trigger** | Poll RSS feeds and upsert new articles | Executes synchronous feed fetch, records status, and invalidates query cache | **WORKING** | None | `POST /ingestion/refresh` mutation | Pytest `test_all.py` |
| **Frontend Production Build** | Compile production bundle cleanly | Strict TypeScript checks pass; bundle built in 727ms | **WORKING** | Unused `React` import in test file | Pruned unused test imports | `pnpm build` (exit code 0) |

---

### Feature Summary
- **Working:** 12 / 12 (100%)
- **Partially Working:** 0
- **Broken:** 0
- **Not Implemented:** 0
- **Blocked:** 0
- **Not Verified:** 0
