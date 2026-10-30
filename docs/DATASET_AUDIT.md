# Dataset Audit & Data Governance

**Project:** NewsLens India  
**Date:** October 30, 2026  

---

## 1. LIAR Benchmark Dataset (Fake News Screening)

- **Source:** Originally published by William Yang Wang (ACL 2017), archived under `research/fake-news-detection/`.
- **License / Terms:** Permitted for academic research, education, and benchmark evaluation.
- **Original Schema:** 14 columns including ID, speaker, context, credit history, and 6-class truth labels (`true`, `mostly-true`, `half-true`, `barely-true`, `false`, `pants-fire`).
- **NewsLens Adaptation:**
  - Evaluated on binary classification: `True / Credible` vs `False / Misleading`.
  - Training Set: 10,240 records (`train.csv`).
  - Held-out Test Set: 2,539 records (after removing 12 duplicate leakage instances present in `test.csv`).
- **Data Quality & Leakage Audit:**
  - String normalization and deduplication conducted before vectorization.
  - TF-IDF vocabulary fitted exclusively on training statements (zero vectorizer contamination).
  - Evaluated on held-out test split (Accuracy: `61.80%`, Macro F1: `0.6158`).

---

## 2. Indian Fact-Check Catalog (`data/fact_checks.json`)

- **Sources:** Official public advisories and press releases from accredited Indian fact-checking bodies:
  - **PIB Fact Check:** Government of India Press Information Bureau.
  - **BOOM Live:** IFCN-certified independent fact-checking organization.
  - **Alt News:** IFCN-certified independent fact-checking news site.
- **Attributes Preserved:**
  - `claim_id`: Unique identifier.
  - `claim`: Verbatim claim text.
  - `verdict`: Genuine verdict (`Fake`, `Misleading`, `False / Out of Context`).
  - `claimant`: Rumor origin / platform.
  - `fact_checker`: Reviewing organization.
  - `review_date`: Verification date.
  - `source_url`: Official debunk link.
  - `explanation`: Contextual breakdown.
- **Ethical Integrity Rule:**
  - NewsLens does **NOT** invent fact-checks. If an queried headline has no close match in the indexed catalog, the system explicitly returns an honest no-data state.

---

## 3. Real-Time News Syndication Feeds

- **Media Outlets:**
  - *The Times of India* (National Top Stories)
  - *The Hindu* (National Feeds)
  - *NDTV* (India News)
  - *The Indian Express* (National Desk)
  - *Hindustan Times* (National News)
  - *Deccan Herald* (National Desk)
- **GDELT 2.0 Doc API:**
  - Search filter: `sourcecountry:IN` and `sourcelang:English`.
- **Attribution & Rights:**
  - Only headlines, publication timestamps, and official permalinks are stored.
  - Every headline links directly to the original publisher URL. No copyright bypass is attempted.
