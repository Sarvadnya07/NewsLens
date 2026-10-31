# NewsLens India — Remediation Progress Journal

**Date:** 2026-10-31 · **Environment:** Windows, Python 3.12.10 (`.venv`) · **Constraint:** Python +
Streamlit only; no framework migration, no destructive git operations, no fabricated results.

Items are listed in the order they were performed. Each stage records what was *observed*, what was
*changed*, and how it was *re-checked*.

---

## Stage 0 — Baseline (before any edit)

| Check | Result |
|---|---|
| `python -m compileall -q app.py src tests` | clean |
| `pip check` | No broken requirements found |
| `pytest -q` | 54 passed |
| `ruff check src tests app.py` | 39 errors, all in 6 modules never imported by app or tests |
| `ruff format --check` | 6 files unformatted |

The 39 lint errors pointed at `src/ml/ml_evaluation.py`, `src/retrieval/retrieval_evaluation.py`,
`src/retrieval/hybrid_retrieval.py`, `src/services/coverage_graph.py`, `src/services/coverage_service.py`,
`src/services/retrieval_service.py`. `grep` confirmed nothing imports them; they described hybrid RRF
retrieval, calibration and coverage-graph features that the product does not have.

**Decision:** quarantine, do not delete and do not falsely complete. Files moved to
`research/experimental/` with a README; `pytest.ini` gained `norecursedirs = research` so quarantined
code cannot be collected as tests. `ruff check` then reported `All checks passed!` over 29 files.

---

## Stage 1 — Reproduce the ML numbers from artifacts

Rather than trust `models/evaluation_metrics.json`, the metrics were recomputed independently in-process
from `models/classifier.joblib`, `models/tfidf_vectorizer.joblib` and the canonical LIAR test partition
(applying the documented overlap filter against `train.tsv`).

| Metric | Recomputed | Stored |
|---|---|---|
| Test samples | 1278 | 1278 |
| Confusion `[[TN,FP],[FN,TP]]` | `[[333,221],[251,473]]` | `[[333,221],[251,473]]` |
| Accuracy | 0.630673 | 0.630673 |
| Macro precision | 0.625881 | 0.625881 |
| Macro recall | 0.627199 | 0.627199 |
| Macro F1 | 0.626187 | 0.626187 |
| Weighted F1 | 0.631634 | 0.631634 |

All matched. The numbers were therefore accepted as genuine and left untouched; only the human-readable
label strings were corrected (see Stage 5).

---

## Stage 2 — Database forensics (read-only, before changes)

- 824 rows, `PRAGMA integrity_check` = `ok`, WAL mode, 4 indexes, 0 duplicate ids, 0 duplicate URLs.
- Publishers: Indian Express 411, Hindustan Times 131, The Hindu 123, NDTV 58, Livemint 55,
  The Times of India 41, `Manual User Submission` 4, `Test Bureau` 1.
- `source_status`: 7 rows — 6 configured feeds `success`, plus a legacy `empty_or_failed` row for the
  retired Deccan Herald feed.
- **Defect found:** 231 of 824 `published_at` values were naive (`2026-10-30 18:32:46`) while the rest
  carried `+00:00`. Sorting and date filters therefore mixed two orderings.

---

## Stage 3 — Timestamp normalization at the domain boundary

- Added `normalize_published_at()` to `src/models.py`; `NormalizedArticle.__post_init__` now coerces
  every incoming value to ISO-8601 UTC and keeps the original in
  `raw_metadata["published_at_raw"]`.
- Added `DatabaseManager.normalize_published_timestamps()` — idempotent, reports the number of rows it
  rewrote, leaves unparseable values intact rather than blanking them.
- Backed up the database to `data/newslens.db.pre_remediation.bak`
  (sha256 `c4af58e0…5ad7`) before touching it.
- Ran the migration once: **231 rows normalized, 0 cleared, 824 → 824 articles**, integrity `ok`,
  sha256 after `2695bbc1…47990`, and a follow-up scan found 0 non-ISO values. A second run reported
  0 changes, confirming idempotency. (A later in-UI GDELT query added one `source_status` row and moved
  the file hash to `830a99c5…39dd1`; no article rows were added or removed.)

---

## Stage 4 — Storage and service contract

- `_connect()` became a context manager: commit on success, rollback on exception, always close
  (previous code leaked connections when a statement raised).
- `_build_filters()` centralises the predicate set (query, `source_type`, publisher, `since_iso`) with
  bound parameters and escaped `LIKE` wildcards (`ESCAPE '\'`).
- `EFFECTIVE_DATE_SQL = COALESCE(NULLIF(published_at,''), ingested_at)` gives undated rows a
  deterministic position in date-ordered queries.
- `ORDER_COLUMNS` whitelists sortable columns; every paged query ends with `, id ASC` so equal
  timestamps cannot shuffle between pages.
- `count_matching_articles()` supplies real totals; `get_distinct_publishers()` feeds the UI dropdown.
- `NewsLensService.query_monitor_articles(..., publisher, days, total_pages, order_by)` returns the
  page plus its total; `get_distinct_publishers()` is exposed for the UI.
- `NewsLensService.__init__` now honours `NEWSLENS_DB_PATH` / `NEWSLENS_FACT_CHECKS_PATH`.

---

## Stage 5 — ML and evidence language

- `src/ml/train.py`: `LOWER_VERACITY_LABEL`, `HIGHER_VERACITY_LABEL`.
- `src/ml/predict.py`: prediction labels and the uncertainty note ("Model Advisory", US LIAR domain
  shift) use the same wording.
- `models/evaluation_metrics.json`: class label strings and `class_semantics` corrected; **every numeric
  field left exactly as verified in Stage 1**.
- `src/ui/pages/methodology.py`: real hyperparameters in the code snippet, "metrics unavailable"
  fallbacks instead of invented values, explanation that the higher-veracity group includes
  *half-true*, and the unverified IFCN claim removed.

---

## Stage 6 — UI repair

| Page | Defect | Repair |
|---|---|---|
| News Monitor | date range and publisher filters inert | both predicates wired to SQL; totals from `count_matching_articles` |
| News Monitor | Prev/Next did not move | real page state, 10 per page, resets on filter-signature change |
| News Monitor | "Dense Table View" badge did nothing | removed |
| News Monitor | Search button ignored input | applies query on click/Enter |
| News Monitor | feed health text was a static string | `_status_label(statuses, feed_count)` |
| News Monitor | GDELT discovery unreachable | explicit **Query GDELT** action reporting the real provider status |
| Overview | `related_count=3 if i%2`, "Flagged for Review", unsupported fact-check badge | removed; counts derived from the actual cluster result; tab renamed "Manual Additions" |
| Overview | threshold hard-coded in copy | read from `service.deduplicator.similar_threshold` |
| Overview | "HEALTHY SOURCES 6 / 7 recorded" | counts the configured registry → "/ 6 configured" |
| Analyze Article | fabricated prefilled claim; Load Example/Clear inert | removed prefill; `pending_article_text` one-shot hand-off makes both buttons and cross-page navigation work |
| Analyze Article / Evidence | similarity always 0% | read `similarity` (was `similarity_score`) |
| Evidence | fact-check total hard-coded | counted from the loaded archive |

---

## Stage 7 — Regression tests

Added to `tests/test_all.py`: `test_normalize_published_at_variants`,
`test_article_normalizes_unparseable_date_and_keeps_raw_metadata`,
`test_published_date_ordering_is_chronological_across_formats`,
`test_normalize_published_timestamps_migrates_legacy_rows`,
`test_monitor_publisher_and_source_filters`, `test_monitor_temporal_scope_and_pagination`,
`test_dedup_related_query_exposes_similarity_key`.

Added to `tests/test_ui.py`: `test_news_monitor_source_filter_is_applied`,
`test_news_monitor_publisher_filter_changes_results`, `test_news_monitor_pagination_controls_exist`,
`test_article_analysis_does_not_prefill_fabricated_article`.

Result: 65 passed in ~6.5 s, `ruff check` clean, `ruff format --check` clean.

---

## Stage 8 — Security and CI

- `bandit -r src app.py -ll` initially reported **2 medium B608** findings in the new filter builder
  (string-concatenated SQL). Assessment: false positive (fixed fragments, bound values). Repair rather
  than suppression: the base statements became module constants `SELECT_ARTICLES_SQL` /
  `COUNT_ARTICLES_SQL`. Re-run: **0 issues** (one pre-existing, justified `# nosec B104` on the
  loopback-host SSRF check).
- `pip-audit --progress-spinner off` → `No known vulnerabilities found`.
- `.github/workflows/ci.yml` triggered on `branches: [master]` while the branch is `main`, so CI had
  never run on this repository. Triggers corrected to `[main, master]`; `pip-audit` step added.
- `pip-audit>=2.7.0` added to `requirements-dev.txt`.
- Added `.streamlit/config.toml` binding `127.0.0.1`, CORS and XSRF on, telemetry off, plus theme
  tokens. Verified with `netstat` (`127.0.0.1:8501` only) and `/_stcore/health` → 200.

---

## Stage 9 — Reproducibility of the test suite

Running the suite from a directory containing only tracked files failed, because `data/liar/`,
`models/*.joblib` and `data/newslens.db` are git-ignored.

- Added explicit guards with reasons: `requires_liar`, `requires_artifacts` (ML tests) and
  `requires_seeded_db` (Streamlit tests, which now probe the datastore read-only).
- Simulated a clean checkout by copying `app.py`, `src/`, `tests/`, `pytest.ini`, `pyproject.toml`,
  `data/fact_checks.json`, `models/evaluation_metrics.json` into a temporary directory:
  **54 passed, 11 skipped, 0 failed**.
- With local data present: **65 passed**.
- Confirmed the suite does not mutate production data: sha256 of `data/newslens.db` was identical
  before and after a full run.

---

## Stage 10 — Live smoke tests

- RSS: 6/6 feeds `success` — TOI 19, The Hindu 60, NDTV 20, Indian Express 200, Hindustan Times 100,
  Livemint 35; per-feed latency 0.55–3.05 s.
- GDELT live query: HTTP **429**, 0 items returned, 11.5 s, recorded status `rate_limited`. Classified
  as an external provider limit; no result inflation and no silent success. The success path remains
  covered only by unit tests — recorded as a verification limit, not a pass.
- Application launched with `python -m streamlit run app.py`, `/_stcore/health` = 200, dashboard
  rendered 824 stored articles, 6 healthy sources, real cluster count, 8 fact-check records.

---

## Stage 11 — Documentation

- `README.md` rewritten: it ended in a UTF-16LE fragment (12 NUL bytes) so tooling saw it as binary.
  Now clean UTF-8/LF with verified counts (824 articles, 65/54+11 tests), the correct dataset path,
  security/verification commands, environment overrides, loopback binding and limitations.
- Added: `COMPREHENSIVE_ISSUE_REGISTER.md` (this audit), this journal, a rewritten `OPEN_ISSUES.md`,
  and a rewritten `FINAL_SYSTEM_ACCEPTANCE_REPORT.md`.
- Removed stale claims: hybrid/RRF retrieval, coverage graph, "calibrated uncertainty", "IFCN
  findings", a GDELT "SQLite cache fallback" that does not exist, "819 articles", "54 tests",
  non-existent `src/common/`.
- Removed stale bytecode (`__pycache__`, including `.pyc` files for deleted modules).

---

## Final verification snapshot

| Command | Result |
|---|---|
| `compileall -q app.py src tests` | clean |
| `pip check` | No broken requirements found |
| `ruff check src tests app.py` | All checks passed |
| `ruff format --check src tests app.py` | 29 files already formatted |
| `pytest -q` | 65 passed in ~6.5 s |
| clean-checkout simulation | 54 passed, 11 skipped |
| `bandit -r src app.py -ll` | 0 issues |
| `pip-audit` | No known vulnerabilities found |
| `streamlit run app.py` + health check | HTTP 200 on loopback |
