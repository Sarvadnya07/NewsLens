# NewsLens India — Final System Acceptance Report

**Date:** 2026-10-31
**Repository:** `C:\Users\ASUS\Desktop\NewsLens-India` (branch `main`, uncommitted remediation in the
worktree — no commit, push or deploy was performed)
**Environment:** Windows 11, Python 3.12.10 in `.venv`, Streamlit modular monolith
**Supersedes:** `docs/FINAL_ACCEPTANCE_REPORT.md` (2026-10-30) and the previous revision of this file,
both of which were written before the repairs below and contained stale counts.

---

## 1. Decision

**ACCEPTED WITH DOCUMENTED LIMITATIONS.**

The application runs, ingests live news, screens text, retrieves evidence and reports provenance
accurately. All defects found in this audit that are inside the repository were fixed and re-verified.
Ten items remain open; none is a silent failure, and each is either external (GDELT rate limiting), a
product boundary (8-record evidence archive, uncalibrated scores, LIAR domain shift), a decision for
the owner (5 legacy test rows, uncommitted dataset/artifacts, `backend/`+`frontend/` scaffolding), or a
deployment concern (single-process Streamlit server). They are recorded in `OPEN_ISSUES.md`.

No fabricated metric, coverage figure, test result or security claim appears in this report; every
number below comes from a command that was executed against this worktree.

---

## 2. What was wrong when the audit began

| Area | Defect | Impact |
|---|---|---|
| News Monitor | date-range and publisher filters were inert | users could not narrow 824 articles |
| News Monitor | Prev/Next did not paginate | only the first page was ever reachable |
| Overview | `related_count = 3 if i % 2`, "Flagged for Review", unsupported fact-check badge | fabricated analysis presented as results |
| Overview | threshold and feed-health strings hard-coded | wrong "6 / 7 recorded" denominator |
| Analyze Article | fabricated prefilled claim; Load Example / Clear inert | page could not be operated as designed |
| Evidence & Analyze | similarity read from a non-existent key | every match displayed 0.0% |
| Data | 231 / 824 `published_at` values in a second, naive format | inconsistent sorting and date filters |
| Storage | connection leak on exception; unescaped `LIKE` wildcards | file locks under reruns; `%` matched everything |
| GDELT | `search_gdelt()` had no caller | "GDELT Discovered" could only ever be empty |
| ML/UI copy | "True/Fake", "calibrated", "IFCN findings" | over-claimed certainty and provenance |
| `src/` | 6 unreachable, partly broken stubs advertising hybrid RRF/coverage-graph features | 39 lint errors; false capability signal |
| Tests | depended on git-ignored data; no regression cover for the above | clean clone could not run; bugs could regress |
| CI | `branches: [master]` on a `main` repository; no dependency audit | CI never ran |
| Docs | `README.md` byte-corrupted (12 NULs, UTF-16 tail) plus stale counts and claims | tooling treated it as binary; figures wrong |

---

## 3. Verification evidence

All commands were run from the repository root with `.venv/Scripts/python.exe`.

| # | Command | Result |
|---|---|---|
| 1 | `python -m compileall -q app.py src tests` | exit 0, no output |
| 2 | `python -m pip check` | `No broken requirements found.` |
| 3 | `python -m ruff check src tests app.py` | `All checks passed!` (29 files) |
| 4 | `python -m ruff format --check src tests app.py` | `29 files already formatted` |
| 5 | `python -m pytest -q` | **65 passed** in 6.2–7.4 s |
| 6 | clean-checkout simulation (no LIAR TSVs, no joblib, no DB) | **54 passed, 11 skipped, 0 failed** |
| 7 | `python -m bandit -r src app.py -ll` | 0 issues (Low/Medium/High all 0); 1 justified `# nosec B104` |
| 8 | `pip-audit --progress-spinner off` | `No known vulnerabilities found` |
| 9 | `streamlit run app.py` + `GET /_stcore/health` | HTTP 200; listener on `127.0.0.1:8501` only |
| 10 | RSS live refresh (all 6 feeds) | 6/6 `success` — TOI 19, The Hindu 60, NDTV 20, Indian Express 200, HT 100, Livemint 35; 0.55–3.05 s |
| 11 | GDELT live query, first via the service and then by pressing **Query GDELT** in the running UI | HTTP 429, 0 items, status `rate_limited`; a `GDELT: India economy` row was recorded in `source_status` with `items_fetched=0` and "GDELT rate limit exceeded (HTTP 429)" — no exception, no fabricated results (external; see OI-01) |
| 12 | `PRAGMA integrity_check` on `data/newslens.db` | `ok`; 824 articles; `journal_mode=wal` |
| 13 | DB mutation check around a full `pytest` run | sha256 unchanged — tests do not write production data (the only hash change during the session came from the UI GDELT action writing its `source_status` row) |

Tests skipped in #6 are reported as skipped with explicit reasons (`requires_liar`,
`requires_artifacts`, `requires_seeded_db`). No assertion was weakened, and nothing was converted from
fail to skip to make the suite look green: with the local dataset present the same suite runs 65 tests.

---

## 4. Machine-learning results validation

The stored metrics were **not** taken on trust. They were recomputed in-process from
`models/classifier.joblib` and `models/tfidf_vectorizer.joblib` over the canonical LIAR test partition,
after removing rows whose normalized text overlaps the training partition.

| Metric | Recomputed | Stored in `models/evaluation_metrics.json` | Match |
|---|---|---|---|
| Test samples | 1278 | 1278 | ✅ |
| Confusion matrix | `[[333,221],[251,473]]` | `[[333,221],[251,473]]` | ✅ |
| Accuracy | 0.630673 | 0.630673 | ✅ |
| Macro precision | 0.625881 | 0.625881 | ✅ |
| Macro recall | 0.627199 | 0.627199 | ✅ |
| Macro F1 | 0.626187 | 0.626187 | ✅ |
| Weighted F1 | 0.631634 | 0.631634 | ✅ |

Only descriptive strings were changed in that file (class names and `class_semantics`); no numeric
value was edited. Reported scores are uncalibrated model outputs on US political statements, and the
UI now says so on every screening result.

---

## 5. Data and storage integrity

- Articles: **824** (unchanged before/after the work; no rows created or deleted).
- `published_at`: 231 legacy naive values normalized to ISO-8601 UTC; 0 unparseable, 0 cleared,
  0 non-ISO remaining; a second migration run changed 0 rows (idempotent).
- Backup retained: `data/newslens.db.pre_remediation.bak` (sha256 `c4af58e0…5ad7`).
  Database sha256 after the timestamp migration: `2695bbc1…47990`; after the UI GDELT action recorded
  its `source_status` row: `830a99c5…39dd1` (articles still 824, integrity `ok`).
- `PRAGMA integrity_check` = `ok`; WAL mode; `busy_timeout=5000`; no duplicate ids or URLs.
- Publishers actually present: Indian Express, Hindustan Times, The Hindu, NDTV, Livemint,
  The Times of India, plus the manual-entry labels from legacy test rows (see OI-02).
- Feed health rows: 6 configured feeds `success`, 1 legacy row for the retired Deccan Herald feed; the
  dashboard now counts only the configured registry.

---

## 6. Per-page functional status (verified in a running instance)

| Page | Status | Notes |
|---|---|---|
| Overview | Working | live counts, real cluster-derived related counts, keyword search, feed tabs, no synthetic badges |
| News Monitor | Working | keyword + source + publisher + date filters, real totals, 10-row pagination, Refresh, and an explicit Query GDELT action that reports the true provider status |
| Analyze Article | Working | starts empty, Load Example / Clear / cross-page hand-off all functional, uncalibrated score + uncertainty flag, similarity percentage populated |
| Evidence & Coverage | Working | BM25Plus retrieval over 8 curated records with real similarity scores, cluster view, honest empty state |
| Methodology & Sources | Working | real hyperparameters, metrics with "unavailable" fallback, limitations, status pills limited to what the code does (NL-34) |

Rendered in a browser against the live server: 824 articles, 6 healthy sources, 100 clusters in the
sample, 8 indexed fact-check claims.

---

## 7. Security posture

- `bandit -ll`: 0 findings. The only suppression is a justified `# nosec B104` on a loopback-host
  rejection check in the SSRF guard (`src/ingestion/rss.py`).
- `pip-audit`: no known vulnerabilities in the audited environment.
- Feed fetching: scheme allowlist (`http`/`https`), per-hop redirect re-validation, private/loopback/
  link-local rejection, 5 MiB streaming cap, explicit timeouts.
- SQL: bound parameters everywhere; `LIKE` wildcards escaped.
- Rendering: `html.escape` on all interpolated article text; no user HTML executed.
- Secrets: none in the repository; `.env`/`.dev.vars` excluded from version control.
- Server: loopback-only binding with CORS/XSRF protection enabled. **Not** hardened for public
  hosting — that would require a proxy, auth and a managed runtime, and was not attempted.

---

## 8. Documentation status

- `README.md` — corrupted bytes removed; verified counts; correct dataset path; setup, verification
  commands, environment overrides, limitations.
- `COMPREHENSIVE_ISSUE_REGISTER.md` — 34 numbered findings with evidence, root cause, repair and
  verification: 29 fixed and verified, 1 fixed with live verification limited to the `rate_limited`
  path, 1 documented but left in place pending an owner decision, 3 investigated and withdrawn as
  non-defects.
- `REMEDIATION_PROGRESS.md` — ordered journal of the work with the commands used.
- `OPEN_ISSUES.md` — 11 open items (10 defects/limitations plus one dev-server operational note) with
  behaviour today and the action required.
- Master project document — calibration, WAL-as-future-work, dashboard-card and label-wording claims
  corrected.
- Stale capability claims removed: hybrid/RRF retrieval, coverage graph, "calibrated uncertainty",
  "IFCN findings", a GDELT SQLite cache fallback that does not exist.

---

## 9. Residual risk

1. **GDELT availability** — HTTP 429 is a provider limit; the app degrades to an explicit status.
2. **Evidence depth** — 8 fact-checks is a demonstration archive, not a verification service.
3. **Model suitability** — LIAR is US political text; Indian news is out of domain, and scores are
   uncalibrated. The UI states this, but the risk cannot be engineered away without new labelled data.
4. **Local data only** — the database, LIAR TSVs and model artifacts are not committed, so a fresh
   clone needs a bootstrap step before the full suite and ingestion can run.
5. **Unowned prior work** — untracked `backend/` and `frontend/` trees remain and are not part of the
   Streamlit product.

---

## 10. Conditions of acceptance

Acceptance of this state is contingent on:

1. Reviewing and deciding on the 5 legacy test rows (OI-02) and the untracked `backend/`/`frontend/`
   trees (OI-03).
2. Treating screening output as an advisory linguistic signal in any demonstration, announcement or
   publication.
3. Re-running the §3 command set before any public claim, since metrics and dependencies can drift.
4. Not publishing this application as a public service without the hosting hardening noted in §7.

---

## 11. Sign-off summary

| Dimension | Verdict |
|---|---|
| Builds / imports | PASS |
| Lint and formatting | PASS (0 findings, 29 files formatted) |
| Automated tests | PASS (65 local; 54 + 11 explicit skips in a clean checkout) |
| ML metric integrity | PASS (independently reproduced, exact match) |
| Data integrity | PASS (824 rows, `integrity_check=ok`, backup retained) |
| Security scans | PASS (Bandit 0, pip-audit clean) |
| UI functional correctness | PASS for all five pages, verified in a live instance |
| Live ingestion (RSS) | PASS (6/6 feeds) |
| Live ingestion (GDELT) | BLOCKED — provider returned HTTP 429; correctly surfaced, not simulated |
| Documentation accuracy | PASS (stale and false claims corrected) |
| Production readiness | NOT CLAIMED — single-process development server, documented limits |

**Final decision: ACCEPTED WITH DOCUMENTED LIMITATIONS**, subject to §10.
