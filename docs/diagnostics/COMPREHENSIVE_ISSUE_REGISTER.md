# NewsLens India — Comprehensive Issue Register

**Project:** NewsLens India — Indian news monitoring and misinformation screening
**Audit date:** 2026-10-31
**Environment:** Windows 11, Python 3.12.10 (`.venv`), Streamlit modular monolith (no migration)
**Scope:** `app.py`, `src/`, `tests/`, `data/`, `models/`, `docs/`, `.github/`

Every entry below was reproduced before repair and re-checked afterwards. "Verified" means the stated
command was actually run in this worktree; unverifiable or externally blocked items are labelled
accordingly and listed in `OPEN_ISSUES.md`.

Severity: **S1** incorrect or fabricated information shown to users · **S2** functional defect ·
**S3** data/consistency defect · **S4** tooling, docs, hygiene.

---

## 1. Summary

| Status | Count |
|---|---|
| Fixed and verified | 29 |
| Fixed, live verification limited (documented) | 1 (NL-17) |
| Documented, awaiting an owner decision (not deleted) | 1 (NL-16) |
| Withdrawn after investigation (not a defect) | 3 (NL-31…NL-33) |

Items that are not fixed at all (external limits, product boundaries, unowned prior work) are
tracked in `OPEN_ISSUES.md` (11 entries, one of them an operational note) rather than here.

Final state: `ruff check` 0 findings, `ruff format --check` clean (29 files), `compileall` clean,
`pip check` clean, `pytest` 65 passed, `bandit -ll` 0 issues, `pip-audit` no known vulnerabilities.

---

## 2. User-facing correctness (S1)

### NL-01 — Temporal filter in News Monitor did nothing
- **Symptom:** Selecting "Last 7 days" / "Last 30 days" changed nothing; all 824 stored articles were
  always returned, including months-old rows.
- **Evidence:** `query_monitor_articles()` had no date parameter; the UI variable was read and
  discarded.
- **Root cause:** Filter widget wired to local state only — feature never implemented end to end.
- **Fix:** `DatabaseManager.query_articles(..., since_iso=...)` and `count_matching_articles(...)`;
  `NewsLensService.query_monitor_articles(..., days=...)` computes the cutoff from
  `EFFECTIVE_DATE_SQL = COALESCE(NULLIF(published_at,''), ingested_at)` so undated rows are still
  filtered deterministically.
- **Verified:** `test_monitor_temporal_scope_and_pagination` plus a manual UI run (the 7-day filter
  reduces the result set and the pagination total updates).

### NL-02 — Publisher filter was inert
- **Symptom:** Publisher dropdown always listed a static list and never filtered results.
- **Root cause:** No publisher predicate in SQL; list hard-coded instead of derived from data.
- **Fix:** `publisher` predicate with bound parameter; `get_distinct_publishers()` populates the
  dropdown from `GROUP BY publisher ORDER BY n DESC`.
- **Verified:** `test_news_monitor_publisher_filter_changes_results` and
  `test_monitor_publisher_and_source_filters` (Indian Express ≠ HT result sets); the dropdown lists
  the 8 distinct publisher values actually stored — the 6 newsrooms plus the two manual-entry labels
  (`Manual User Submission`, `Test Bureau`) that legacy test rows carry.

### NL-03 — Pagination controls did not paginate
- **Symptom:** "Next"/"Previous" rendered but the page slice never advanced.
- **Root cause:** Total count was hard-coded; `offset` stayed at 0; filter changes did not reset the
  page.
- **Fix:** `count_matching_articles()` provides the real total, `total_pages` is computed from it,
  `st.session_state` page index resets on a filter signature change, and `ORDER BY <col> <dir>, id ASC`
  makes page boundaries stable for equal timestamps.
- **Verified:** `test_news_monitor_pagination_controls_exist`,
  `test_monitor_temporal_scope_and_pagination` and `test_database_pagination_and_sorting` (page 1 and
  page 2 disjoint, 10 per page, filter changes reset the index).

### NL-04 — Dashboard displayed fabricated signals
- **Symptom:** "Flagged for Review" badges were produced by `i % 2`, "related coverage" counts were
  literal `3`, and a fact-check match badge was asserted without any retrieval call.
- **Root cause:** Placeholder values left in the render path and presented as analysis.
- **Fix:** Removed synthetic counters. Related-coverage counts now come from the real clustering
  result; the manual tab is labelled "Manual Additions" (fact, not an allegation); the  fact-check badge is gone. Domain counts come from parsed article URLs via the `AUTHORITATIVE_FEEDS`
  registry.
- **Verified:** `test_app_test_initial_load` renders the page; `grep -rn "Flagged for Review" src`
  returns no matches (the only remaining reference was a stale comment, now corrected).

### NL-05 — Simulation thresholds shown as if they were configured values
- **Symptom:** "similarity ≥ 0.55" was hard-coded in the dashboard copy.
- **Fix:** Read from `service.deduplicator.similar_threshold`, so the printed threshold follows the
  configuration.

### NL-06 — Evidence coverage reported 0% similarity for every article
- **Symptom:** Every BM25 hit showed `0.0%` similarity.
- **Root cause:** Key mismatch — the UI read `similarity_score`, the retrieval result exposes
  `similarity`.
- **Fix:** Both `evidence_coverage.py` and `article_analysis.py` read `similarity`; the "no evidence"
  explanation cites `QUERY_MIN_SIMILARITY` (0.15) from `src/processing/deduplication.py`.

### NL-07 — Analyze Article carried a fabricated prefilled claim
- **Symptom:** The page opened with example text that was not user input, and "Load Example"/"Clear"
  appeared to do nothing.
- **Root cause:** The text area was initialised from a module-level constant and those buttons wrote to
  a key that was overwritten on the next rerun.
- **Fix:** Removed the prefilled claim; added a `pending_article_text` widget-state hand-off pattern
  (`st.session_state["pending_article_text"]` consumed once, then cleared) so Load Example, Clear, and
  "Screen in ML Analyzer" from the monitor all work.
- **Verified:** `test_article_analysis_does_not_prefill_fabricated_article`,
  `test_app_test_article_screening_flow`, and a manual UI run of Load Example → Clear.

### NL-08 — Misleading ML class labels in shipped artifacts and UI
- **Symptom:** Output was described as "True"/"Fake" and the metrics file used `Fake`/`True` class
  names, implying a factual verdict from a LIAR-trained stylistic model.
- **Fix:** `LOWER_VERACITY_LABEL` / `HIGHER_VERACITY_LABEL` in `src/ml/train.py`; predictions read
  "Lower-veracity linguistic pattern" / "Higher-veracity linguistic pattern"; the uncertainty note
  states the US LIAR domain shift; `models/evaluation_metrics.json` class label strings and
  `class_semantics` were corrected **without touching any numeric value**; methodology page explains
  that the higher-veracity group includes *half-true*.

### NL-09 — "Calibrated uncertainty" and "IFCN findings" claims
- **Symptom:** UI and docs asserted calibrated probabilities and IFCN-sourced findings.
- **Reality:** The classifier is uncalibrated and the archive is 8 locally curated records with no
  IFCN validation.
- **Fix:** Copy states "uncalibrated model score" and "locally curated archive"; the IFCN claim was
  removed. The 0.15 margin is described as a decision-margin heuristic, not a calibrated interval.

### NL-10 — Fact-check total hard-coded
- **Symptom:** Pages printed a fixed count while the archive changed.
- **Fix:** Count derived from the loaded `fact_checks.json` records (currently 8).

### NL-34 — Methodology status pills asserted unimplemented capability
- **Symptom:** The ethical-framework cards on *Methodology & Sources* carried green tick pills reading
  "Linguistic Drift Monitored" and "Real-Time Caution Threshold". The Analyze Article subtitle also
  claimed "forensic lexical calibration".
- **Evidence:** `grep -rni "drift" src` returns no monitoring code; no temporal caution/alerting logic
  exists anywhere in `src/`; the classifier is explicitly uncalibrated (see NL-09).
- **Fix:** Pills now read "⚠ No Drift Monitoring" and "⚠ No Automated Alerts" in the caution colour, and
  the subtitle says "lexical pattern analysis". Nothing was implemented to match the old wording.
- **Verified:** Re-rendered `?page=methodology` and `?page=analyze` in the running app; the strings are
  absent from the DOM and the corrected text is present. `pytest -q` 65 passed afterwards.

---

## 3. Data integrity (S3)

### NL-11 — Mixed timestamp formats in `articles.published_at`
- **Symptom:** 231 of 824 rows stored naive local-looking strings (`2026-10-30 18:32:46`) while RSS
  rows stored ISO-8601 with offset (`...+00:00`). Sorting and date filtering were therefore
  inconsistent, and UI timestamps alternated between two formats.
- **Root cause:** RFC-822 feed timestamps were formatted at ingestion without a shared convention;
  GDELT `seendate` parsing used a second, different convention.
- **Fix:** `normalize_published_at()` in `src/models.py`, enforced by `NormalizedArticle.__post_init__`
  (the domain boundary), preserving the original value in `raw_metadata["published_at_raw"]`. All
  write paths (RSS, GDELT, manual) now share it.
- **Migration:** idempotent one-off `DatabaseManager.normalize_published_timestamps()` executed once
  against the real database: 231 rows normalized, 0 cleared, 0 non-ISO values remaining.
- **Safety:** backup taken first — `data/newslens.db.pre_remediation.bak`
  (sha256 `c4af58e0…5ad7`). Post-migration: 824 articles before and after,
  `PRAGMA integrity_check` = `ok`, sha256 after the migration `2695bbc1…47990`. A later browser check of
  the GDELT action appended one legitimate `source_status` row, so the current file hash is
  `830a99c5…39dd1`; the article count (824) and integrity result are unchanged.
- **Verified:** `test_normalize_published_at_variants`,
  `test_article_normalizes_unparseable_date_and_keeps_raw_metadata`,
  `test_published_date_ordering_is_chronological_across_formats`,
  `test_normalize_published_timestamps_migrates_legacy_rows`.

### NL-12 — SQLite connections leaked per call
- **Symptom:** `sqlite3.connect()` results were closed only on the happy path; an exception left the
  handle (and its file lock) open, which matters under Streamlit's rerun-heavy execution and WAL mode.
- **Fix:** `_connect()` is a context manager that always commits/closes and rolls back on error.

### NL-13 — No stable ordering for equal timestamps
- **Fix:** Every paged query appends `, id ASC`; verified by a pagination test with duplicate
  `published_at` values.

### NL-14 — Unescaped `LIKE` wildcards in search
- **Symptom:** A query containing `%` or `_` behaved as a wildcard and could match nearly everything.
- **Fix:** `_build_filters()` escapes `\`, `%`, `_` and applies `ESCAPE '\'`; values remain bound
  parameters.
- **Verified:** `test_database_literal_wildcard_search`.

### NL-15 — Stale feed-health denominator
- **Symptom:** Dashboard read "6 / 7 recorded" because a retired feed (Deccan Herald) still had a
  legacy `empty_or_failed` row.
- **Fix:** The card counts only feeds in the current registry (`/ 6 configured`); legacy rows are
  retained in the table as the historical record rather than deleted.

### NL-16 — Test submissions present in the production database
- **Observation:** 5 `source_type='manual'` rows created by automated sessions
  (`post-restart-head-check`, `restage-reconciliation-gate`, `final-commit-decision-after-restage`,
  `post-final-commit-reconfirm`, `Automated Unit Test Headline for Verification`) appear in the
  Overview and News Monitor feeds.
- **Action taken:** documented, not deleted — the brief forbids destructive changes to user data.
  `OPEN_ISSUES.md` lists the exact IDs and a review-then-delete SQL statement.
- **Also verified:** the current suite does not write to the production database. sha256 of
  `data/newslens.db` was identical before and after a full `pytest` run.

---

## 4. Functional gaps (S2)

### NL-17 — GDELT search existed but was unreachable
- **Symptom:** `NewsLensService.search_gdelt()` implemented throttling, retries and status taxonomy
  but no UI or test called it; the "GDELT Discovered" tab could only ever be empty.
- **Fix:** News Monitor now has an explicit **Query GDELT** action that runs one bounded request for
  the current search text, prints the true provider status (`success`, `rate_limited`, `timeout`,
  `provider_unavailable`, …) and never claims results it did not store.
- **Verification limit:** the live endpoint returned HTTP 429 from this network during the audit, so
  only the `rate_limited` path was exercised live. Success/parse paths are covered by unit tests with
  recorded payloads.

### NL-18 — "Dense Table View" badge was inert
- **Fix:** removed rather than faked.

### NL-19 — Search button did not apply the typed query
- **Fix:** the query is applied on click (and on Enter), and the pager resets.

### NL-20 — Six unreachable stub modules in `src/`
- **Files:** `ml_evaluation.py`, `retrieval_evaluation.py`, `hybrid_retrieval.py`, `coverage_graph.py`
  (`src/services/`), `coverage_service.py`, `retrieval_service.py`.
- **Why they were a problem:** never imported by the app or tests, they advertised hybrid RRF
  retrieval, calibration and coverage-graph features the product does not implement; five of them had
  `ruff` violations and none had tests.
- **Decision:** non-destructively quarantined to `research/experimental/` with a README explaining the
  status, and excluded from `pytest` via `norecursedirs = research`. They were neither deleted nor
  falsely completed.
- **Result:** `ruff check` and `ruff format --check` became clean (29 files).

---

## 5. Security review

### NL-21 — Dependency audit was not part of CI
- **Fix:** `pip-audit` added to `requirements-dev.txt` and to the CI workflow.

### NL-22 — SQL construction pattern flagged by Bandit (B608)
- **Detail:** the new dynamic filter builder concatenated generated fragments onto a literal
  `"SELECT ... WHERE 1=1"`, which Bandit reports as possible SQL injection (2 medium issues).
- **Assessment:** false positive — fragments are fixed strings and all values are bound.
- **Fix:** the base statements are module constants (`SELECT_ARTICLES_SQL`, `COUNT_ARTICLES_SQL`), so
  the pattern disappears without any `# nosec` suppression.
- **Verified:** `bandit -r src app.py -ll` → 0 issues (1 pre-existing justified `# nosec B104` for the
  loopback-host SSRF check).

### NL-23 — Development server binding
- **Finding:** the repository shipped no `.streamlit/config.toml`, so bind address and CORS/XSRF
  behaviour depended on the machine.
- **Fix:** added `.streamlit/config.toml` — `address = "127.0.0.1"`, `enableCORS = true`,
  `enableXsrfProtection = true`, `gatherUsageStats = false`, plus the theme tokens.
- **Verified:** `netstat` shows `127.0.0.1:8501` only; `/_stcore/health` returns 200.

### NL-24 — Existing controls confirmed (no change required)
Feed scheme allowlist, per-hop redirect re-validation, private/loopback rejection, 5 MiB streaming
cap, explicit timeouts, `html.escape` on all interpolated article text, bound SQL parameters, and
model artifacts loaded only from project-owned paths.

---

## 6. Tests and reproducibility

### NL-25 — Tests depended on untracked data (`data/liar/`, `models/*.joblib`, `data/newslens.db`)
- **Symptom:** a clean clone fails at collection/assertions because those paths are git-ignored.
- **Fix:** explicit `pytest.mark.skipif` guards with reasons (`requires_liar`, `requires_artifacts`,
  `requires_seeded_db`) and a read-only datastore check. `NewsLensService` gained
  `NEWSLENS_DB_PATH` / `NEWSLENS_FACT_CHECKS_PATH` overrides.
- **Verified by simulation:** a temporary directory containing only tracked files (no LIAR TSVs, no
  joblib, no database) ran `54 passed, 11 skipped, 0 failed`. With local data present: `65 passed`.
- **Honesty note:** skips are explicit and reported; no assertion was weakened and nothing is marked
  as passed when it did not run.

### NL-26 — CI never ran
- **Symptom:** `.github/workflows/ci.yml` triggered on `branches: [master]` while the repository
  branch is `main`.
- **Fix:** triggers on `main` and `master`; added the `pip-audit` step.

### NL-27 — New regression coverage
- 7 domain/service/storage tests in `tests/test_all.py`
  (`test_normalize_published_at_variants`,
  `test_article_normalizes_unparseable_date_and_keeps_raw_metadata`,
  `test_published_date_ordering_is_chronological_across_formats`,
  `test_normalize_published_timestamps_migrates_legacy_rows`,
  `test_monitor_publisher_and_source_filters`, `test_monitor_temporal_scope_and_pagination`,
  `test_dedup_related_query_exposes_similarity_key`) and 4 UI tests in `tests/test_ui.py`
  (`test_news_monitor_source_filter_is_applied`, `test_news_monitor_publisher_filter_changes_results`,
  `test_news_monitor_pagination_controls_exist`,
  `test_article_analysis_does_not_prefill_fabricated_article`). Suite: 54 → 65 tests, all passing in
  ~6.5 s.

---

## 7. Documentation

### NL-28 — `README.md` was byte-corrupted
- **Symptom:** the file ended with a UTF-16LE fragment (`#\x00 \x00N\x00…`), 12 NUL bytes in total, so
  `git diff`, `grep` and review tools treated it as binary.
- **Fix:** rewritten as clean UTF-8/LF with verified figures: 824 stored articles, 65/54+11 test
  outcomes, correct dataset path (`data/liar/`), `pip-audit`/`bandit` commands, environment
  overrides, loopback binding, and an explicit limitations section.

### NL-29 — Stale or overstated claims across documents
- **Corrected:** "819 canonical RSS records" → 824 (verified count); "54 of 54 tests" → 65; references
  to a non-existent `src/common/` package; "FULLY ACCEPTED" status before re-verification; "calibrated
  uncertainty"; "transparent fallback to the local SQLite article cache" in GDELT (no cache fallback
  exists — the status is surfaced instead); hybrid-retrieval/RRF and coverage-graph capability claims
  (not implemented; the stubs are quarantined).
- **Verified:** `grep` over `README.md` and `docs/` for the removed claims returns no matches.

### NL-30 — Missing diagnostics artefacts
- **Fix:** this register, `REMEDIATION_PROGRESS.md`, a rewritten `OPEN_ISSUES.md`, and a rewritten
  `FINAL_SYSTEM_ACCEPTANCE_REPORT.md` (measured evidence, honest statuses).

---

## 8. Investigated and withdrawn (not defects)

| ID | Suspicion | Finding |
|---|---|---|
| NL-31 | ML metrics in `models/evaluation_metrics.json` could be unverified | Independently recomputed from `classifier.joblib` + `tfidf_vectorizer.joblib` on the canonical test partition: N=1278, `[[333,221],[251,473]]`, accuracy 0.630673, macro P/R/F1 0.625881/0.627199/0.626187, weighted F1 0.631634 — all match the file |
| NL-32 | Duplicate-leakage guard might be cosmetic | 7 validation and 5 test statements are removed by normalized-text overlap against train; counts reproduce exactly |
| NL-33 | RSS ingestion might be broadly broken | Live smoke: 6/6 feeds `success` (TOI 19, The Hindu 60, NDTV 20, Indian Express 200, HT 100, Livemint 35; 0.55–3.05 s) |

---

## 9. Open items

See `OPEN_ISSUES.md`. In brief: GDELT HTTP 429 from this network (external), 5 legacy manual test rows
in the local database awaiting a decision, untracked `backend/` + `frontend/` migration scaffolding
out of scope for this Python/Streamlit system, 8-record fact-check archive, uncommitted dataset and
model artifacts, no GDELT response cache, uncalibrated scores, and LIAR→Indian-news domain shift.
