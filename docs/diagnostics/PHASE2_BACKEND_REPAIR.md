# NewsLens India — Phase 2: Backend, External APIs, Ingestion & Database Repair Report

**Document Status:** Complete & Verified Engineering Report  
**Date:** 2026-10-31  
**Target System:** NewsLens India (`C:\Users\ASUS\Desktop\NewsLens-India`)  
**Active Environment:** Python 3.12.10 (.venv), SQLite 3.x, Streamlit 1.43.0, Scikit-learn 1.9.1  
**Database Checkpoint:** `data/newslens.db` (Pristine 819 articles preserved, verified with `data/newslens.db.phase1.bak`)  
**Baseline Test Suite:** **41/41 passing automated tests** (24 existing + 17 comprehensive Phase 2 tests)  

---

## Executive Summary

Phase 2 engineering repairs focused on hardening the core ingestion pipeline, external API integrations (GDELT Doc API and curated Indian publisher RSS feeds), persistence layers (SQLite `DatabaseManager`), and internal service contracts (`NewsLensService`).

All repairs adhered strictly to the **Python modular monolith** architecture constraint: no external microservices, brokers, or secondary databases were introduced. All repairs preserve existing database records (819 articles and 7 source status records), eliminate swallowed exceptions, ensure idempotent upserts, provide literal LIKE escaping, and establish typed result models.

---

## 1. Canonical Contracts Established

Canonical data models were standardized in `src/ingestion/models.py` without overlapping or duplicating the core `NormalizedArticle` model:

### Standardized Status Taxonomy
```python
STATUS_SUCCESS = "success"
STATUS_NO_RESULTS = "no_results"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_TIMEOUT = "timeout"
STATUS_PROVIDER_UNAVAILABLE = "provider_unavailable"
STATUS_INVALID_RESPONSE = "invalid_response"
STATUS_DISABLED = "disabled"
STATUS_NOT_ATTEMPTED = "not_attempted"
```

### Result & Error Models
- **`ProviderFetchResult`**: Canonical per-source result encapsulating `source_id`, `source_name`, `source_type`, `status`, `articles`, `items_count`, `duration_ms`, `error_message`, and `last_attempt_at`.
- **`RefreshResult`**: Canonical return object for multi-source synchronous refresh operations (`total_fetched`, `new_stored`, `duration_ms`, `provider_results`, `all_succeeded`, `all_failed`).
- **`ProviderError`** hierarchy: `ProviderRateLimitedError`, `ProviderTimeoutError`, `ProviderInvalidResponseError` with automated path and credential sanitization for user-facing safety.

---

## 2. GDELT Doc API Integration Repair

### Changes Implemented (`src/ingestion/gdelt.py`)
1. **Endpoint & Filtering:** Verified against GDELT 2.0 Doc API specs (`https://api.gdeltproject.org/api/v2/doc/doc`). Formats queries with keyword, `sourcecountry:IN`, and `sourcelang:English`.
2. **Explicit Timeouts & Throttling:** Configured connect/read timeout (15s default) and 5.0s minimum interval throttle between sequential queries.
3. **Bounded Retries:** Single retry for eligible transient timeouts and connection failures (`max_retries=1`, `retry_delay_seconds=2.0`).
4. **Typed Status Classification:**
   - HTTP 429 returns `STATUS_RATE_LIMITED`.
   - HTTP 5xx returns `STATUS_PROVIDER_UNAVAILABLE`.
   - Timeout returns `STATUS_TIMEOUT`.
   - HTML or non-JSON payloads return `STATUS_INVALID_RESPONSE`.
   - Empty `articles` array returns `STATUS_NO_RESULTS`.
   - Valid articles return `STATUS_SUCCESS` with SHA-256 canonical URL article IDs (`gdelt_<hash[:16]>`).
5. **Contract:** Added `fetch_articles(...) -> ProviderFetchResult` while retaining backward-compatible `search_articles(...) -> List[NormalizedArticle]`.

---

## 3. RSS Feed Ingestion Hardening

### Changes Implemented (`src/ingestion/rss.py`)
1. **Authoritative Monitored Feed Registry:**
   Consolidated into `AUTHORITATIVE_FEEDS` containing exactly 6 real, verified Indian national and business news publications:
   - *The Times of India (National)*
   - *The Hindu (National)*
   - *NDTV (India News)*
   - *Indian Express (India)*
   - *Hindustan Times (India)*
   - *Livemint (National & Economy)*
2. **Bounded HTTP Streaming:**
   - Configured `requests.Session` with `stream=True` and `timeout=(10, 10)`.
   - Enforced `MAX_FEED_BYTES = 5 * 1024 * 1024` (5 MiB). Any feed exceeding 5MB is safely aborted with `STATUS_INVALID_RESPONSE`.
3. **Redirect & SSRF Safety:**
   - Maximum redirects capped at 4 (`_MAX_REDIRECTS = 4`).
   - Disallowed non-HTTP/HTTPS schemes.
   - Rejected redirects to loopback (`localhost`, `127.0.0.1`, `0.0.0.0`, `::1`) and private IP ranges (`10.x`, `192.168.x`, `169.254.x`).
4. **Feed Failure Isolation:**
   - Each feed download and parse is wrapped independently in `fetch_feed_result(...)`.
   - A network failure or malformed XML in one feed never halts or degrades the remaining feeds.
5. **Normalization & Provenance:**
   - Canonicalized URL tracking parameter stripping.
   - Deterministic SHA-256 article ID generation (`rss_<sha256(canon_url)[:16]>`).
   - Publication timestamp parsing with fallback to raw string without fabricating timestamps.

---

## 4. SQLite Database Persistence Integrity

### Changes Implemented (`src/storage/database.py`)
1. **Thread-Safety & Locking:**
   - Enabled WAL mode (`PRAGMA journal_mode=WAL`).
   - Configured busy timeout to 5000ms (`PRAGMA busy_timeout=5000`).
   - Bounded lock retry exponential backoff for operational lock errors.
2. **Idempotent Upsert:**
   - `upsert_article` and `upsert_articles` inspect existing record IDs to accurately report whether a row was inserted new or updated on conflict.
   - Batch upsert wrapped in an explicit transaction (`with self._get_connection() as conn: ... conn.commit()`).
3. **Literal LIKE Wildcard Escaping:**
   - Implemented `escape_like_literal(query)` escaping `%`, `_`, and `\`.
   - Queries use parameterized `WHERE (title LIKE ? ESCAPE '\' OR summary LIKE ? ESCAPE '\' OR query LIKE ? ESCAPE '\')`.
4. **Pagination & True Total Counting:**
   - Implemented `count_matching_articles(query, source_type)` calculating total matching rows independently from page limits.
   - `get_articles` supports parameterized `limit`, `offset`, `order_by`, and `ascending`.

---

## 5. News Monitor Service Contract

### Changes Implemented (`src/services/news_service.py`)
1. **Composed Query Method:**
   Added `query_monitor_articles(...)` returning:
   ```python
   {
       "articles": List[NormalizedArticle],
       "total_matching": int,
       "page": int,
       "page_size": int,
       "applied_filters": {
           "query": Optional[str],
           "source_type": Optional[str],
           "sort_order": str,
       },
   }
   ```
2. **Distinguishing Filters vs Defaults:**
   - Empty search inputs (`""` or `"All Monitored Streams"`) evaluate strictly to `query=None` (no text filter applied).
   - "All" sources correctly clears `source_type=None` rather than filtering to a single provider.
3. **Synchronous Ingestion Orchestration:**
   - `refresh_rss_feeds()` executes synchronously, upserts new records, records per-feed health outcomes in SQLite, and returns a structured `RefreshResult`.
   - Partial successes are preserved and returned to the UI.

---

## 6. Verification & Automated Test Suite

A dedicated regression test suite was created in `tests/test_backend_phase2.py`:
- `test_gdelt_success`: Verifies GDELT payload normalization and tracking param stripping.
- `test_gdelt_empty_result`: Verifies empty article payload returns `STATUS_NO_RESULTS`.
- `test_gdelt_429_rate_limit`: Verifies 429 response returns `STATUS_RATE_LIMITED`.
- `test_gdelt_timeout`: Verifies timeout returns `STATUS_TIMEOUT`.
- `test_gdelt_invalid_payload`: Verifies non-JSON/HTML payload returns `STATUS_INVALID_RESPONSE`.
- `test_rss_success`: Verifies bounded RSS streaming download and XML parsing.
- `test_rss_empty_feed`: Verifies empty XML feed returns `STATUS_NO_RESULTS`.
- `test_rss_malformed_feed`: Verifies broken XML returns `STATUS_INVALID_RESPONSE`.
- `test_rss_oversized_feed`: Verifies responses > 5MB are rejected.
- `test_rss_timeout`: Verifies RSS connection timeouts return `STATUS_TIMEOUT`.
- `test_rss_redirect_restrictions`: Verifies loopback/disallowed redirect rejections.
- `test_partial_and_all_providers_failing`: Verifies partial failure preservation.
- `test_database_idempotent_upsert`: Verifies accurate inserted vs updated return flags.
- `test_database_literal_wildcard_search`: Verifies `%` and `_` are matched literally.
- `test_database_pagination_and_sorting`: Verifies offset/limit and total count.
- `test_database_transaction_rollback_on_failure`: Verifies atomic rollback on failure.
- `test_news_monitor_service_contract`: Verifies structured query contract.

### Test Execution Summary
```bash
pytest -v
============================= 41 passed in 4.37s ==============================
```

### Live API Verification
- **Curated RSS Feeds:** Verified live HTTP 200 connectivity to all 6 feeds (TOI, The Hindu, NDTV, Indian Express, Hindustan Times, Livemint).
- **GDELT Doc API:** Live public endpoint returned HTTP 429 during unthrottled burst testing, confirming our rate-limiting and 429 handling correctly classifies the response rather than converting it to a false empty result.
