# NewsLens India — Remaining Defects & Known Environmental Limitations

## Active Defects
**Total Defects: 0**  
All reported P0, P1, and P2 functional defects have been resolved and verified through automated tests and live browser execution.

---

## Known External / Environmental Limitations

### 1. GDELT v2 Doc API External Throttling (HTTP 429)
- **Status:** Handled gracefully.
- **Details:** The public upstream GDELT 2.0 Doc API periodically enforces rate limits on automated queries.
- **Handling:** NewsLens India implements exponential backoff, records `'rate_limited'` status in `source_status`, and falls back to cached SQLite articles without crashing or hanging the application.

### 2. Scikit-Learn Cross-Version Unpickling Warning
- **Status:** Harmless notice.
- **Details:** The binary model artifacts (`models/classifier.joblib`, `models/tfidf_vectorizer.joblib`) emit `InconsistentVersionWarning` when unpickled across minor versions (1.9.1 vs 1.7.2).
- **Handling:** The missing attribute compatibility layer (`multi_class = 'auto'`) was applied in `src/ml/predict.py`. Inference executes deterministically with 100% test pass rate.

### 3. Production SQLite Database Isolation
- **Status:** Protected.
- **Details:** The live production database `data/newslens.db` contains 824 articles and is backed up at `data/newslens.db.backup`. All automated unit and integration tests execute against isolated in-memory or temporary SQLite database instances.
