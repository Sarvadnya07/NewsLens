# Test Execution Report

**Date of Execution:** October 30, 2026
**Environment:** Windows | Python 3.12.10 | Pytest 9.2.0 | Ruff 0.15.1
**Target:** NewsLens India Test Suite (`tests/test_all.py` and `tests/test_ui.py`)

---

## 1. Test Summary

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\ASUS\Desktop\NewsLens-India\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\ASUS\Desktop\NewsLens-India
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 23 items

tests/test_all.py::test_clean_text_basic PASSED                          [  4%]
tests/test_all.py::test_clean_text_empty_and_none PASSED                 [  8%]
tests/test_all.py::test_tokenize_text PASSED                             [ 13%]
tests/test_all.py::test_canonicalize_url PASSED                          [ 17%]
tests/test_all.py::test_ml_model_loading_and_inference PASSED            [ 21%]
tests/test_all.py::test_ml_model_empty_and_short_input PASSED            [ 26%]
tests/test_all.py::test_gdelt_normalization_mocked PASSED                [ 30%]
tests/test_all.py::test_gdelt_rate_limit_and_error_handling PASSED       [ 34%]
tests/test_all.py::test_gdelt_transient_retry_success PASSED             [ 39%]
tests/test_all.py::test_rss_feed_parsing_mocked PASSED                   [ 43%]
tests/test_all.py::test_rss_malformed_feed_handling PASSED               [ 47%]
tests/test_all.py::test_fact_check_retrieval_match PASSED                [ 52%]
tests/test_all.py::test_fact_check_retrieval_empty_corpus PASSED         [ 56%]
tests/test_all.py::test_fact_check_retrieval_empty_query PASSED          [ 60%]
tests/test_all.py::test_fact_check_retrieval_zero_overlap_no_false_positive PASSED [ 65%]
tests/test_all.py::test_deduplicator_clusters PASSED                     [ 69%]
tests/test_all.py::test_sqlite_persistence PASSED                        [ 73%]
tests/test_all.py::test_service_manual_submission_and_retrieval PASSED   [ 78%]
tests/test_ui.py::test_ui_imports PASSED                                 [ 82%]
tests/test_ui.py::test_app_test_initial_load PASSED                      [ 86%]
tests/test_ui.py::test_app_test_page_navigation PASSED                   [ 91%]
tests/test_ui.py::test_app_test_article_screening_flow PASSED            [ 95%]
tests/test_ui.py::test_app_test_url_query_param_sync PASSED              [100%]

============================= 23 passed in 3.99s ==============================
```

- **Total Tests:** 23
- **Passed:** 23 (100%)
- **Failed:** 0
- **Warnings:** 0 (cleanly retrained under scikit-learn 1.9.1 / Python 3.12 without `InconsistentVersionWarning`)
- **Ruff Linting Status:** 0 errors (all checks passed)
- **Ruff Formatting Status:** 23 files cleanly formatted

---

## 2. Tested Components

| Component | Coverage Focus | Result |
| :--- | :--- | :--- |
| **Preprocessing** | HTML stripping, URL removal, punctuation cleaning, tokenization | PASS |
| **ML Inference** | Zero-token, short-token (<3 terms), standard headline inference, probability calibration | PASS |
| **GDELT Ingestion** | Parameter normalization, 429 rate limit handling, transient retry with backoff, connection error safety | PASS |
| **RSS Ingestion** | Parsing standard feeds, malformed XML fault-tolerance, UTM canonicalization | PASS |
| **BM25 Fact-Check** | Claim matching, empty corpus resilience, zero-token queries, lexical token-overlap guard preventing false positives | PASS |
| **Deduplication** | Cosine similarity clustering (exact duplicates vs. related coverage) | PASS |
| **Persistence** | SQLite schema creation, article upsert, telemetry tracking, idempotence | PASS |
| **Service Layer** | Manual article submission, end-to-end orchestration | PASS |
| **UI Components** | Multi-page Streamlit navigation, AppTest initial load, parameter syncing | PASS |
