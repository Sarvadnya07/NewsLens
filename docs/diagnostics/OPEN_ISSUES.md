# NewsLens India — Open Issues

**Date:** 2026-10-31 · **Scope of this document:** items that are *not* fixed, with the reason and the
action required. Nothing in this file is a silent failure; each entry states how the system behaves
today.

Status legend: **EXTERNAL** (outside the repository's control) · **DECISION NEEDED** (requires the
owner) · **OUT OF SCOPE** (belongs to prior, unrelated work) · **KNOWN LIMITATION** (documented
product boundary).

---

### OI-01 — GDELT DOC API returns HTTP 429 from this network — EXTERNAL

- **Observed:** a live `search_gdelt` call on 2026-10-31 returned HTTP 429 after 11.5 s with 0 items;
  the recorded status was `rate_limited`.
- **Behaviour:** the status is surfaced verbatim in the News Monitor toast and in `source_status`;
  nothing is presented as a successful empty result and no rows are invented.
- **Not implemented:** a cached-result fallback. Earlier documentation claimed one; there is none. The
  client retries a bounded number of times with a fixed delay and then reports the provider status.
- **Needed to close:** provider-side relief (longer interval, different egress, or a sanctioned mirror).
  No code change in this repository can make the public endpoint accept more requests.

### OI-02 — Five automated test submissions remain in the local database — DECISION NEEDED

- **Rows** (`source_type='manual'`), visible in Overview and News Monitor:

  | id | title |
  |---|---|
  | `manual_929e310f6da32413` | Automated Unit Test Headline for Verification |
  | `manual_dc55b30b360fdf11` | post-final-commit-reconfirm |
  | `manual_71b6793cba71c937` | final-commit-decision-after-restage |
  | `manual_ff12875304e89343` | restage-reconciliation-gate |
  | `manual_8a86903b5b838eb9` | post-restart-head-check |

- **Why they are still there:** the remediation brief forbids destructive changes to user data, so
  they were left in place and documented instead of deleted.
- **Impact:** cosmetic noise in the feeds; the `Test Bureau` and `Manual User Submission` values also
  appear in the publisher filter.
- **To remove, after review** (a backup already exists at
  `data/newslens.db.pre_remediation.bak`):

  ```sql
  DELETE FROM articles
  WHERE id IN ('manual_929e310f6da32413','manual_dc55b30b360fdf11','manual_71b6793cba71c937',
               'manual_ff12875304e89343','manual_8a86903b5b838eb9');
  ```

- **Prevention:** the current suite is verified not to write to `data/newslens.db` (hash unchanged
  across a full run); these rows predate that verification.

### OI-03 — Untracked `backend/` (FastAPI) and `frontend/` (Vite/React) trees — OUT OF SCOPE

- **What they are:** an unfinished alternative implementation left in the worktree by earlier work.
  The production application is, and remains, Python + Streamlit.
- **Why untouched:** adding them to the build or deleting them are both outside this remediation's
  mandate; they are unreferenced by `app.py`, `src/` and `pytest`.
- **Impact:** none at runtime; they do add noise to `git status` and they pull in dependencies that
  `requirements.txt` deliberately does not include.
- **Needed:** an owner decision — delete, archive, or complete them as a separate project.

### OI-04 — Fact-check evidence archive contains 8 records — KNOWN LIMITATION

- `data/fact_checks.json` holds 8 curated Indian fact-checks (PIB Fact Check, Alt News, BOOM Live).
- Retrieval is BM25Plus over those records; no live synchronization and no IFCN signatory validation
  exists. The UI now states "locally curated archive" and no longer claims IFCN provenance.
- Growing the archive is a content task, not a code defect.

### OI-05 — Dataset and model artifacts are not committed — KNOWN LIMITATION

- `data/liar/*.tsv` and `models/*.joblib` are git-ignored (see `.gitignore`), and `data/newslens.db`
  holds local state. A clean clone therefore cannot run the 11 artifact-dependent tests.
- **Current behaviour:** those tests skip with an explicit reason
  (`requires_liar`, `requires_artifacts`, `requires_seeded_db`); a simulated clean checkout yields
  54 passed / 11 skipped / 0 failed. Nothing is falsely reported as passing.
- **To close:** either commit the artifacts (a licensing/size decision for the owner — LIAR
  redistribution terms and a ~460 KB binary payload) or add a bootstrap step that fetches the dataset
  and retrains before CI runs the full suite.

### OI-06 — Classifier scores are uncalibrated — KNOWN LIMITATION

- Output is a decision-function-derived score from class-balanced Logistic Regression, not a
  probability of factual truth. The UI labels it "uncalibrated model score" and flags predictions
  within a 0.15 margin as *Uncertain / Insufficient Model Signal*.
- **To close:** calibration study (Platt/isotonic) on a held-out partition, plus reliability curves in
  the evaluation report. This is research work, not a bug fix.

### OI-07 — LIAR (US political statements) → Indian news domain shift — KNOWN LIMITATION

- The benchmark and the application domain differ in register, topic and style. Stated in the
  prediction advisory and on the Methodology page.
- **To close:** in-domain labeled data for Indian news, which does not currently exist in this
  repository.

### OI-08 — Legacy `source_status` row for a retired feed — KNOWN LIMITATION

- Deccan Herald has an `empty_or_failed` row from before the feed registry changed. It is retained as
  history; the dashboard now counts only configured feeds ("/ 6 configured").
- Removing it is a data decision, deliberately not taken unilaterally.

### OI-09 — Coverage counts are similarity clusters, not independent corroboration — KNOWN LIMITATION

- Many "separate" reports are the same wire copy. The UI labels clusters as exact republishing
  (`≥ 0.90`), likely syndication (`≥ 0.70`) and similar coverage (`≥ 0.55`) and does not describe them
  as verification.

### OI-10 — Streamlit is a single-process development server — KNOWN LIMITATION

- `.streamlit/config.toml` binds `127.0.0.1` with CORS/XSRF enabled. For multi-user hosting the app
  needs a reverse proxy, authentication and a managed deployment; no production deployment was
  performed or claimed as part of this work.

---

### OI-11 — Streamlit does not hot-reload edited `src/` modules on this Windows setup — OPERATIONAL NOTE

**Observed:** while verifying NL-34, edits to `src/ui/pages/methodology.py` and
`src/ui/pages/article_analysis.py` were not reflected in the running server even across full browser
reloads; the old strings kept rendering from `sys.modules` until the server process was restarted.
`.streamlit/config.toml` does not disable the file watcher, so this is environment/tooling behaviour,
not configuration. `app.py` itself still re-runs.

**Impact:** you can spend time debugging copy that is already correct in the file. There is no user-facing
effect and nothing is broken in the app.

**Workaround:** restart `streamlit run app.py` after editing anything under `src/`.

---

## Resolved during this remediation

Everything else audited was fixed and re-verified — see
`COMPREHENSIVE_ISSUE_REGISTER.md` for the full list (inert date/publisher filters, broken pagination,
fabricated dashboard signals, 0%-similarity key mismatch, inert Analyze Article controls, mixed
timestamp formats across 231 rows, connection leak, `LIKE` wildcard injection, unreachable GDELT query
path, unreachable `src/` stubs, Bandit B608 pattern, CI never triggering, missing `pip-audit`, missing
Streamlit config, corrupted README, stale capability claims) and `REMEDIATION_PROGRESS.md` for the
order of work.
