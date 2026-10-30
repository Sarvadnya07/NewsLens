# Test Execution Report

**Date of Execution:** October 30, 2026  
**Environment:** Windows | Python 3.13.9 | Pytest 9.1.1 | Ruff 0.16.3  

---

## 1. Test Summary

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ASUS\Desktop\NewsLens-India
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, dash-3.3.0, asyncio-1.4.0, cov-6.0.0, mock-3.15.1, requests-mock-1.12.1
collecting ... collected 16 items

tests/test_all.py::test_clean_text_basic PASSED                          [  6%]
tests/test_all.py::test_clean_text_empty_and_none PASSED                 [ 12%]
tests/test_all.py::test_tokenize_text PASSED                             [ 18%]
tests/test_all.py::test_canonicalize_url PASSED                          [ 25%]
tests/test_all.py::test_ml_model_loading_and_inference PASSED            [ 31%]
tests/test_all.py::test_ml_model_empty_and_short_input PASSED            [ 37%]
tests/test_all.py::test_gdelt_normalization_mocked PASSED                [ 43%]
tests/test_all.py::test_gdelt_rate_limit_and_error_handling PASSED       [ 50%]
tests/test_all.py::test_rss_feed_parsing_mocked PASSED                   [ 56%]
tests/test_all.py::test_rss_malformed_feed_handling PASSED               [ 62%]
tests/test_all.py::test_fact_check_retrieval_match PASSED                [ 68%]
tests/test_all.py::test_fact_check_retrieval_empty_corpus PASSED         [ 75%]
tests/test_all.py::test_fact_check_retrieval_empty_query PASSED          [ 81%]
tests/test_all.py::test_deduplicator_clusters PASSED                     [ 87%]
tests/test_all.py::test_sqlite_persistence PASSED                        [ 93%]
tests/test_all.py::test_service_manual_submission_and_retrieval PASSED   [100%]

============================= 16 passed in 1.75s ==============================
```

- **Total Tests:** 16
- **Passed:** 16 (100%)
- **Failed:** 0
- **Warnings:** 0
- **Ruff Linting Status:** 0 errors (all checks passed)
- **Ruff Formatting Status:** 18 files cleanly formatted
