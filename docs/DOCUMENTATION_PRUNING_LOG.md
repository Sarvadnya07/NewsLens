# NewsLens India — Documentation Pruning, Scope Alignment & Content Classification Log

**Document Purpose:** Complete forensic log of the content classification, pruning, merging, moving, and refinement actions performed to transform the oversized 20-chapter master document into a focused, academically rigorous 8-chapter project report (`docs/NEWSLENS_INDIA_MASTER_PROJECT_DOCUMENTATION.md`).
**Execution Date:** October 31, 2026  
**Auditor / Editor:** Senior Academic Technical Writer, Documentation Architect & ML Researcher  
**Governing Standard:** Documentation Kernel (Strict Source-of-Truth Hierarchy & Preservation-First Rule)  

---

## 1. Chapter-by-Chapter Content Classification Matrix

Every chapter and substantial subsection from the 20-chapter baseline was audited and categorized according to the four-tier classification model:
- **Category A (Essential: Keep):** Information directly required to explain the project academically and technically.
- **Category B (Important but Repetitive: Merge):** Useful information that repeats other sections; consolidated into a single clear location.
- **Category C (Supporting Engineering Detail: Move):** Implementation, maintenance, or operational runbook content moved to existing audit reports or concise appendices.
- **Category D (Irrelevant, Redundant or Out of Scope: Remove):** Speculative roadmaps, exaggerated prose, repetitive diagram variations, and unnecessary administrative filler.

| Original 20-Chapter Section | Classification | Action Taken | Rationale & Destination |
| :--- | :---: | :---: | :--- |
| **Front Matter & Document Control** | Cat B / Cat C | **Refined & Pruned** | Removed repetitive compliance summaries and internal agent governance logs. Retained clean academic front matter (Title, Domain, Author, Version, Date, TOC). Full document control remains tracked in `docs/MASTER_DOCUMENTATION_SOURCE_MAP.md`. |
| **Chapter 1: Executive Summary** | Cat B | **Merged into Ch. 1** | Consolidated with Introduction to eliminate three consecutive redundant explanations of what the project does. |
| **Chapter 2: Introduction & Research Motivation** | Cat A / Cat B | **Merged into Ch. 1** | Forms the foundation of Chapter 1 (Background, Motivation, Problem Context). |
| **Chapter 3: Problem Statement & Engineering Goals** | Cat A / Cat B | **Merged into Ch. 1** | Forms Section 1.3 of the new Chapter 1 (Problem Statement & Core Challenges). |
| **Chapter 4: Objectives, Scope & System Boundaries** | Cat A / Cat B | **Merged into Ch. 1** | Forms Section 1.5 of the new Chapter 1 (Objectives, Explicit Scope, In-Scope vs. Out-of-Scope Boundaries). |
| **Chapter 5: Literature Review & Existing Systems** | Cat A | **Retained as Ch. 2** | Retained with clean academic citations (Wang 2017, Robertson & Zaragoza 2009, Lv & Zhai 2011, Leetaru 2013). Removed general AI textbook filler; focused strictly on news aggregation, TF-IDF, Logistic Regression, BM25, and multi-source evidence gaps. |
| **Chapter 6: Proposed System Architecture & Operational Workflow** | Cat B | **Merged into Ch. 3** | Consolidated with Chapter 8 into a single, cohesive architecture chapter with unified workflow and data flow descriptions. |
| **Chapter 7: System Requirements & Technology Stack** | Cat A / Cat B | **Merged into Ch. 3** | Requirements (FRs and NFRs) and technology stack table consolidated into Chapter 3 (Sections 3.3, 3.4, 3.5). |
| **Chapter 8: System Architecture & Design** | Cat A / Cat B | **Retained as Ch. 3** | Forms the core of Chapter 3. Pruned 5 redundant variations of diagrams down to 3 high-impact, non-redundant Mermaid diagrams: (1) Overall System Architecture, (2) ML Training & Screening Pipeline, and (3) End-to-End Multi-Source News & Evidence Workflow. |
| **Chapter 9: Data Sources, Datasets & Data Governance** | Cat A | **Retained as Ch. 4** | Merged into Chapter 4 (Dataset and Methodology). Ingestion sources (RSS, GDELT), canonical LIAR provenance, 14-column schema, `QUOTE_NONE` solution, and SQLite persistence consolidated cleanly. |
| **Chapter 10: Machine Learning Methodology & Mathematical Foundations** | Cat A | **Retained as Ch. 4** | Core ML section of Chapter 4. Retained sublinear TF-IDF, unigrams/bigrams, balanced Logistic Regression, loss formulations, and leakage prevention. Pruned repetitive elementary KaTeX equations. |
| **Chapter 11: Fact-Check Retrieval & Evidence Matching** | Cat A | **Retained as Ch. 4** | Retrieval section of Chapter 4. Explains Okapi BM25Plus, floor offset rationale, pre-retrieval lexical token overlap guard, and authentic seed catalog. |
| **Chapter 12: Cross-Publisher Duplicate & Related Coverage Clustering** | Cat A | **Retained as Ch. 4** | Clustering section of Chapter 4. Details URL canonicalization, TF-IDF cosine similarity, similarity thresholds ($\ge 0.90, \ge 0.70, \ge 0.55$), and syndication vs. corroboration. |
| **Chapter 13: User Interface Architecture & Page Workflows** | Cat A | **Retained as Ch. 5** | Forms Chapter 5 (System Implementation & User Interface). Explains the five actual Streamlit pages, Stitch design tokens, interactive states, and component rendering. |
| **Chapter 14: Implementation Details & Codebase Modularization** | Cat B / Cat C | **Merged into Ch. 5** | Replaced line-by-line file walkthroughs with a clean, concise directory layout and module responsibility matrix. Detailed line-by-line function catalogs preserved in `docs/IMPLEMENTATION_STATUS.md`. |
| **Chapter 15: Experimental Evaluation, Results & Error Analysis** | Cat A | **Retained as Ch. 6** | Core evaluation section of Chapter 6. Exact verified metrics preserved: Accuracy (63.07%), Macro-F1 (0.6262), Weighted-F1 (0.6316), Confusion Matrix (`[[333, 221], [251, 473]]`), error taxonomy, and domain shift analysis. |
| **Chapter 16: Software Testing, Quality Assurance & Verification** | Cat A / Cat C | **Merged into Ch. 6** | Summarized 26 automated tests into categories (preprocessing, ML, ingestion, retrieval, deduplication, SQLite, UI AppTest) and verification commands. Removed bloated 26-row test table from main body (already preserved in `docs/TEST_REPORT.md` and Appendix C). |
| **Chapter 17: Security, Reliability, Operations & Incident Recovery** | Cat C | **Moved to Runbook / Ch. 7** | Essential security principles (parameterized SQL, XSS escaping, safe deserialization) summarized in Chapter 3/4. Detailed disaster recovery shell scripts moved to `docs/RECOVERY_RUNBOOK.md`. |
| **Chapter 18: System Limitations & Responsible AI Disclosures** | Cat A | **Retained as Ch. 7** | Core limitations section of Chapter 7 (Limitations and Future Scope). Preserved domain shift, binary compression, GDELT 429 throttling, lexical BM25 matching, and seed catalog boundaries. |
| **Chapter 19: Future Enhancements & Research Roadmap** | Cat D / Cat B | **Pruned into Ch. 7** | Removed speculative 5-phase enterprise cloud roadmap (Kubernetes, Celery, Prometheus, MuRIL). Replaced with a concise, realistic academic future scope: Indian-context datasets, vernacular support, hybrid dense retrieval, and dynamic ClaimReview scraping. |
| **Chapter 20: Conclusion & Engineering Summary** | Cat A | **Retained as Ch. 8** | Concise academic conclusion summarizing problem, solution, implementation, empirical findings, and Responsible AI contribution without repeating previous chapters. |
| **References & Academic Citations** | Cat A | **Retained** | Verified 10 legitimate academic citations (Wang 2017, Robertson & Zaragoza 2009, Lv & Zhai 2011, Leetaru 2013, Pedregosa 2011, Thorne 2018, Augenstein 2019, McKee 2026, Brown 2020, Patel 2017). |
| **Appendices A–E** | Cat C / Cat A | **Consolidated to A–D** | - Appendix A: Canonical LIAR 14-Column Schema (Retained).<br>- Appendix B: Key Dependencies & Setup Commands (Retained).<br>- Appendix C: Summary of Automated Test Suite (Consolidated).<br>- Appendix D: Canonical Data Model Specifications (Consolidated).<br>- Raw full transcripts and repetitive test inventories pruned from report body. |

---

## 2. Structural Consolidation Mapping

```
Original 20 Chapters + 5 Appendices                    Refined Academic Structure (8 Chapters + 4 Appendices)
======================================                 ======================================================
Front Matter & Governance                              Front Matter (Clean Academic Title, Author, TOC)
Chapter 1: Executive Summary                           
Chapter 2: Introduction & Motivation           ===>    Chapter 1: Introduction, Problem Statement & Scope
Chapter 3: Problem Statement
Chapter 4: Objectives & Scope
-------------------------------------------------------------------------------------------------------------
Chapter 5: Literature Review & Existing        ===>    Chapter 2: Literature Review & Existing Approaches
-------------------------------------------------------------------------------------------------------------
Chapter 6: Proposed System & Workflow
Chapter 7: Requirements & Tech Stack           ===>    Chapter 3: Proposed System & Architecture
Chapter 8: System Architecture (5 Diagrams)            (Unified Architecture, 3 Focused Diagrams)
-------------------------------------------------------------------------------------------------------------
Chapter 9: Data Sources & Provenance
Chapter 10: ML Methodology & Equations         ===>    Chapter 4: Dataset & Methodology
Chapter 11: Fact-Check Retrieval                       (Ingestion, LIAR TSV, ML, BM25Plus, Cosine Clustering, SQLite)
Chapter 12: Deduplication & Clustering
-------------------------------------------------------------------------------------------------------------
Chapter 13: UI Architecture & Pages            ===>    Chapter 5: System Implementation & User Interface
Chapter 14: Implementation Details & Codebase          (5 Streamlit Pages, Stitch Design, Module Responsibility)
-------------------------------------------------------------------------------------------------------------
Chapter 15: Experimental Evaluation & Results  ===>    Chapter 6: Testing, Results & Discussion
Chapter 16: Software Testing & QA                      (Test Strategy, 63.07% Accuracy, Confusion Matrix, Discussion)
-------------------------------------------------------------------------------------------------------------
Chapter 17: Security & Disaster Recovery       ===>    Chapter 7: Limitations & Future Scope
Chapter 18: System Limitations                         (Explicit Limitations, Concise Academic Future Scope;
Chapter 19: Future Enhancements (5 Phases)              Disaster recovery moved to RECOVERY_RUNBOOK.md)
-------------------------------------------------------------------------------------------------------------
Chapter 20: Conclusion & Summary               ===>    Chapter 8: Conclusion
-------------------------------------------------------------------------------------------------------------
References (10 Citations)                      ===>    References (10 Verified Academic Citations)
Appendices A–E                                 ===>    Appendices A–D (Pruned, Focused Technical References)
```

---

## 3. Preservation Verification

- **Supporting Audit Reports Preserved Intact:** All 11 original technical reports under `docs/` (`DATASET_AUDIT.md`, `LIAR_PROVENANCE_RECONCILIATION.md`, `ML_EVALUATION_REPORT.md`, `FINAL_ACCEPTANCE_REPORT.md`, `IMPLEMENTATION_STATUS.md`, `TEST_REPORT.md`, `VERIFICATION_REPORT.md`, `ENGINEERING_AUDIT.md`, `ENVIRONMENT_AUDIT.md`, `RECOVERY_RUNBOOK.md`, `REPOSITORY_AUDIT.md`) remain untouched in the repository.
- **Backup Created:** `docs/NEWSLENS_INDIA_MASTER_PROJECT_DOCUMENTATION.md.bak` (165,114 bytes) was preserved before editing.
- **Source Code & Data Untouched:** Zero application code, database rows, or model weights were altered.
