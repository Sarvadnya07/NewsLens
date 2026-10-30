# System Verification Report

**Project:** NewsLens India
**Date:** October 30, 2026
**Auditor / Lead Engineer:** Senior Python Engineer & QA Specialist
**Environment:** `.venv\Scripts\python.exe` (Python 3.12.10, Windows 11)
**Test Suite:** 20 automated tests | **Passing:** 20 / 20 (100%) | **Warnings:** 0

---

## 1. Feature Verification Matrix

| Subsystem / Feature | Verification Status | Verification Method | Notes |
|---|---|---|---|
| **Virtual Environment & Dependencies** | **Verified** | `pip check` & core import script | Isolated `.venv` with Python 3.12.10. All packages declared and resolving cleanly. |
| **Ruff Linting** | **Verified** | `.venv\Scripts\python.exe -m ruff check src tests app.py` | 0 errors. All imports sorted, unused variables resolved, HTML escaping secure. |
| **Ruff Formatting** | **Verified** | `.venv\Scripts\python.exe -m ruff format --check src tests app.py` | 23 project files cleanly formatted. |
| **Text Preprocessing** | **Verified** | Automated unit tests | HTML/URL stripping, lowercasing, unicode normalization, tokenization. |
| **URL Canonicalization** | **Verified** | Automated unit tests | Strips UTM tracking params, cleans fragments and trailing slashes. |
| **ML Artifact Loading & Inference** | **Verified** | Automated integration tests | Retrained with Python 3.12 / scikit-learn 1.9.1; zero deprecation/version warnings. |
| **Empty/Short Input Handling** | **Verified** | Automated unit tests | Safe fallback states for empty text and text < 2 words. |
| **GDELT Doc Ingestion** | **Verified against live service & mock** | Live query + mocked unit tests | Verified live response (status 200) + 5s rate-limit throttling. |
| **RSS Ingestion** | **Verified against live service & mock** | Live refresh + mocked unit tests | 6 verified feeds (TOI, The Hindu, NDTV, IE, HT, Livemint) returning 435+ articles. |
| **BM25Plus Fact-Check Match** | **Verified** | Automated unit tests | Okapi BM25Plus retrieval over verified Indian claims with match advisories. |
| **BM25 Empty/No-Match Corpus** | **Verified** | Automated unit tests | Honest no-match handling when query finds no relevant fact-check. |
| **Deduplication & Clustering** | **Verified** | Automated unit tests | Differentiates exact/republished, likely syndicated, and similar coverage. |
| **SQLite Persistence** | **Verified** | Automated integration tests | Thread-safe transactions, parameterized queries, and restart persistence. |
| **End-to-End Service Flow** | **Verified** | Integration test | Complete flow: manual ingest -> ML score -> BM25 search -> related news. |
| **Streamlit AppTest Suite** | **Verified** | Automated headless AppTest | Full programmatic testing of initial render, 5-page navigation, and screening. |
| **Streamlit Dashboard (Live HTTP)** | **Verified** | Live background server | Responding with HTTP 200 on port 8501, HTML-escaped UI components. |

---

## 2. Test Execution Output

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.2.0, pluggy-1.7.0 -- .venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\ASUS\Desktop\NewsLens-India
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collecting ... collected 20 items

tests/test_all.py::test_clean_text_basic PASSED                          [  5%]
tests/test_all.py::test_clean_text_empty_and_none PASSED                 [ 10%]
tests/test_all.py::test_tokenize_text PASSED                             [ 15%]
tests/test_all.py::test_canonicalize_url PASSED                          [ 20%]
tests/test_all.py::test_ml_model_loading_and_inference PASSED            [ 25%]
tests/test_all.py::test_ml_model_empty_and_short_input PASSED            [ 30%]
tests/test_all.py::test_gdelt_normalization_mocked PASSED                [ 35%]
tests/test_all.py::test_gdelt_rate_limit_and_error_handling PASSED       [ 40%]
tests/test_all.py::test_rss_feed_parsing_mocked PASSED                   [ 45%]
tests/test_all.py::test_rss_malformed_feed_handling PASSED               [ 50%]
tests/test_all.py::test_fact_check_retrieval_match PASSED                [ 55%]
tests/test_all.py::test_fact_check_retrieval_empty_corpus PASSED         [ 60%]
tests/test_all.py::test_fact_check_retrieval_empty_query PASSED          [ 65%]
tests/test_all.py::test_deduplicator_clusters PASSED                     [ 70%]
tests/test_all.py::test_sqlite_persistence PASSED                        [ 75%]
tests/test_all.py::test_service_manual_submission_and_retrieval PASSED   [ 80%]
tests/test_ui.py::test_ui_imports PASSED                                 [ 85%]
tests/test_ui.py::test_app_test_initial_load PASSED                      [ 90%]
tests/test_ui.py::test_app_test_page_navigation PASSED                   [ 95%]
tests/test_ui.py::test_app_test_article_screening_flow PASSED            [100%]

============================= 20 passed in 3.55s ==============================
```

---

## 3. Reproduction Commands (Windows CMD & PowerShell)

```cmd
:: 1. Compile all source files
.venv\Scripts\python.exe -m compileall -q .

:: 2. Check code style and linting
.venv\Scripts\python.exe -m ruff check src tests app.py
.venv\Scripts\python.exe -m ruff format --check src tests app.py

:: 3. Execute test suite
.venv\Scripts\python.exe -m pytest -v

:: 4. Launch live Streamlit web application
.venv\Scripts\python.exe -m streamlit run app.py
```
