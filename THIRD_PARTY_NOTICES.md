# Third-Party Notices & Open Source Attributions

NewsLens India integrates and builds upon concepts and components from the following open-source projects:

---

## 1. rank_bm25
- **Author:** Dorian Brown
- **Repository:** `research/rank_bm25` (PyPI package `rank_bm25`)
- **License:** Apache License 2.0
- **Usage:** Algorithmic BM25Plus retrieval engine over verified Indian fact-check corpus.

---

## 2. feedparser
- **Authors:** Kurt McKee, Mark Pilgrim
- **Repository:** `research/feedparser` (PyPI package `feedparser`)
- **License:** BSD 2-Clause License
- **Usage:** Syndicated Indian news aggregator (Times of India, The Hindu, NDTV, Indian Express, Hindustan Times).

---

## 3. GDELT 2.0 Doc API Client
- **Author:** Alex Whitehead-Smith
- **Repository:** `research/gdelt-doc-api`
- **License:** MIT License
- **Usage:** Reference query schema and parameter structures for GDELT 2.0 Doc API. Production implementation in `src/ingestion/gdelt.py` features custom 5-second rate throttling, timeout handling, and schema normalization.

---

## 4. Fake News Detection & LIAR Benchmark
- **Author:** Nishit Patel (reference code), William Yang Wang (LIAR dataset benchmark)
- **Repository:** `research/fake-news-detection`
- **Citation:** William Yang Wang, "Liar, Liar Pants on Fire": A New Benchmark Dataset for Fake News Detection, ACL 2017.
- **License:** MIT License
- **Usage:** LIAR benchmark dataset (`train.csv`, `test.csv`) used to train our reproducible Scikit-Learn TF-IDF + Logistic Regression screening model with duplicate leakage elimination. All legacy pickle files were discarded and replaced with verified Joblib artifacts.
