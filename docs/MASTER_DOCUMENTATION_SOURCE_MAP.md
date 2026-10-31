# NewsLens India — Master Documentation Source Mapping Matrix

**Document Purpose:** Exhaustive trace of all project source documentation, audit logs, configuration files, and research repositories synthesized into the refined authoritative master document (`docs/NEWSLENS_INDIA_MASTER_PROJECT_DOCUMENTATION.md`).  
**Updated:** October 31, 2026 (Refined Academic Edition v2.0.0)  
**Auditor / Architect:** Senior Academic Technical Writer, Documentation Architect & ML Researcher  
**Governing Standard:** Documentation Kernel & Preservation-First Rule  

---

## 1. Primary Source Inventory & Incorporation Matrix (Refined 8-Chapter Structure)

| Source Path | Original Document Title | Scope & Nature | Extraction Status | Target Chapter in Refined Master Report | Retained / Excluded Justification |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `README.md` | NewsLens India README | Gateway / Overview | Integrated | Ch. 1, 3, 5, App. B | High-level project identity, core workflows, technology stack, and runbook integrated into main report. |
| `docs/LIAR_PROVENANCE_RECONCILIATION.md` | LIAR Dataset Provenance & Record Discrepancy Reconciliation | Definitive Provenance Audit | **Fully Current & Canonical** | Ch. 4 (Sec 4.2, 4.3), App. A | Exact root cause of 29 train & 16 test record absorption by RFC 4180 parsers, `QUOTE_NONE` solution, SHA-256 hashes, and 14-column schema incorporated. |
| `docs/ML_EVALUATION_REPORT.md` | ML Evaluation Report: Fake News Screening Model | Canonical ML Benchmark | **Fully Current & Canonical** | Ch. 4 (Sec 4.5), Ch. 6 (Sec 6.3, 6.4, 6.5) | Canonical metrics (Acc: 0.6307, Macro F1: 0.6262, Weighted F1: 0.6316, confusion matrix `[[333, 221], [251, 473]]`) fully integrated into Chapter 6. |
| `docs/DATASET_AUDIT.md` | Dataset Audit & Data Governance | Data Governance Ledger | **Partially Superseded / Updated** | Ch. 4 (Sec 4.1, 4.4, 4.8) | Explains 14 LIAR fields, 6-to-2 label collapse, fact-check seed catalog schema, and Deccan Herald-to-Livemint transition. |
| `docs/FINAL_ACCEPTANCE_REPORT.md` | Final Acceptance Report & Demonstration Readiness Audit | Engineering Audit & Acceptance | **Partially Superseded / Historical** | Ch. 3 (Sec 3.5), Ch. 6 (Sec 6.1, 6.2) | Documents live RSS feed smoke test (6/6 HTTP 200), GDELT 429 rate limit finding, SQLite 666-record state, and Streamlit AppTest passes. Historical 23-test metrics updated to 26. |
| `docs/IMPLEMENTATION_STATUS.md` | Comprehensive Implementation & Functional Audit | Subsystem Breakdown | **Historical Baseline** | Ch. 3 (Sec 3.6), Ch. 4 (Sec 4.6, 4.7), Ch. 5 | Deep architectural review of subsystems, BM25Plus zero-overlap finding, deduplication thresholds, and service orchestration. |
| `docs/TEST_REPORT.md` | Test Execution Report | Test Evidence Record | **Historical Baseline (23 tests)** | Ch. 6 (Sec 6.1, 6.2), App. C | Test breakdown across preprocessing, URL canonicalization, ML, BM25, and UI AppTests. Summarized into 8 categories. |
| `docs/VERIFICATION_REPORT.md` | System Verification Report | Feature Verification Matrix | **Historical Baseline (20 tests)** | Ch. 3 (Sec 3.3, 3.4), Ch. 6 | Verification matrix of core functional criteria, security parameters, and Ruff formatting passes. |
| `docs/ENGINEERING_AUDIT.md` | Engineering Audit & Hardening Log | Defect Log & Hardening History | **Historical Log** | Ch. 4 (Sec 4.1), Ch. 5 (Sec 5.5) | Specific hardening records: Deccan Herald 404 outage resolution with Livemint, URL canonicalization tracking-tag stripping, and SHA-256 ID migration. |
| `docs/ENVIRONMENT_AUDIT.md` | Environment Audit & Python Specification | Python Environment Diagnostic | **Historical Diagnostic** | Ch. 3 (Sec 3.5), App. B | Python 3.12 vs 3.13 dual-installation root cause, `.venv` isolation policy, and PowerShell execution instructions. |
| `docs/REPOSITORY_AUDIT.md` | REPOSITORY AUDIT: Research Codebase Inspection | Research Code Audit | **Historical Analysis** | Ch. 2 (Sec 2.4, 2.5), Ch. 5 | Audit of the 4 reference sub-repositories under `research/`. Confirmed policy of zero binary pickle loading and independent native implementation. |
| `docs/RECOVERY_RUNBOOK.md` | Operational Runbook: Disaster Recovery & Incident Response | Operational Procedures | **Supporting Operational Runbook** | Preserved in `RECOVERY_RUNBOOK.md`; summarized in Ch. 5 (Sec 5.5) | Detailed disaster recovery shell commands moved out of primary academic report into dedicated runbook. |
| `stitch_.../DESIGN.md` | NewsLens India Investigative Intelligence Design Specs | UI/UX Design System | **Fully Current** | Ch. 5 (Sec 5.3) | Color tokens (surface: `#f8f9ff`, primary: `#00253d`, secondary: `#00696d`), typography rules (Newsreader + Inter), and editorial card layouts. |
| `models/evaluation_metrics.json` | Model Evaluation Metrics | **Machine Source of Truth** | **Canonical Data** | Ch. 4, Ch. 6 | Machine-verified performance metrics and confusion matrix values for canonical LIAR evaluation. |
| `data/fact_checks.json` | Verified Indian Fact-Check Catalog | Canonical Retrieval Corpus | **Canonical Data** | Ch. 4 (Sec 4.6), App. D | 8 accredited seed fact-check records from PIB Fact Check, BOOM Live, and Alt News. |

---

## 2. Research Sub-Repositories Traceability

| Research Subtree | Upstream Origin | Role in NewsLens India | Implementation Choice in NewsLens |
| :--- | :--- | :--- | :--- |
| `research/fake-news-detection/` | `nishitpatel01/Fake_News_Detection` (Commit `880a278`) | Reference implementation of LIAR classification with scikit-learn models. | Re-implemented natively in `src/ml/train.py` and `src/ml/predict.py`. Raw pickle weights (`final_model.sav`, `model.pkl`) completely excluded for security. Canonical TSVs parsed via `csv.QUOTE_NONE`. |
| `research/rank_bm25/` | `dorianbrown/rank_bm25` (PyPI `rank_bm25`) | BM25 retrieval algorithms (BM25Okapi, BM25L, BM25Plus). | Installed via pip and utilized in `src/retrieval/fact_check.py` with added corpus vocabulary overlap guard. |
| `research/gdelt-doc-api/` | `alex9smith/gdelt-doc-api` (PyPI `gdeltdoc`) | Client wrapper for GDELT 2.0 Doc API. | Hardened native client in `src/ingestion/gdelt.py` featuring 5s rate throttling, 15s timeout, and 1-attempt transient retry. |
| `research/feedparser/` | `kurtmckee/feedparser` (PyPI `feedparser`) | Syndication feed parser. | Installed via pip and wrapped in `src/ingestion/rss.py` with per-feed error isolation. |
