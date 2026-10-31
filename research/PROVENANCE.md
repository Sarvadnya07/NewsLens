# Research Provenance & Reference Repositories

## 1. Overview
During initial prototyping and research, four external repositories were referenced.
To maintain repository hygiene and minimize bloat, their thousands of upstream source files have been removed from the active repository checkout.
The canonical LIAR dataset splits required for reproducible model training and evaluation have been directly relocated to `data/liar/`.

---

## 2. Upstream Reference Repositories

| Repository Role | Upstream URL | Commit Reference | Purpose & Status |
|---|---|---|---|
| **Fake News Detection (LIAR)** | `https://github.com/nishitpatel01/Fake_News_Detection.git` | `880a2782ab627c10e4f9cf98c3d753d48439a9d1` | Source of canonical LIAR benchmark dataset splits. Canonical TSVs (`train.tsv`, `valid.tsv`, `test.tsv`), license, and provenance notes preserved in `data/liar/`. Full repo checkout pruned. |
| **Feedparser** | `https://github.com/kurtmckee/feedparser.git` | `a22c5521cbb109871f1a2318948581901bd47e26` | Reference implementation for RSS parsing. NewsLens India consumes the official wheel via PyPI (`feedparser>=6.0.10`). Full cloned repo pruned. |
| **GDELT Doc API** | `https://github.com/alex9smith/gdelt-doc-api.git` | `41220163fbab99982e4dca3a05d25a95b49896d7` | Reference wrapper for GDELT 2.0 Doc API. NewsLens India implements direct, hardened REST querying in `src/ingestion/gdelt.py`. Full cloned repo pruned. |
| **Rank BM25** | `https://github.com/dorianbrown/rank_bm25.git` | `47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099` | Reference implementation for BM25 algorithms. NewsLens India consumes the official wheel via PyPI (`rank_bm25>=0.2.2`). Full cloned repo pruned. |

---

## 3. Preservation & Attribution
- All required dataset files are permanently preserved under `data/liar/` with exact SHA-256 validation.
- Full upstream repository clones are permanently backed up externally at `..\NewsLens-India-Backup-Pass2\research\`.
