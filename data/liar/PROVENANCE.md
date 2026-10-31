# LIAR Benchmark Dataset — Provenance & Licensing

## 1. Overview
This directory contains the canonical benchmark dataset splits for the **LIAR** dataset (William Yang Wang, "Liar, Liar Pants on Fire: A New Benchmark Dataset for Fake News Detection", ACL 2017).

- **Source Reference:** https://github.com/nishitpatel01/Fake_News_Detection / Original ACL 2017 paper
- **License:** MIT License (see `LICENSE` in this directory)
- **Role:** Ground-truth training, validation, and test splits for the TF-IDF + Logistic Regression misinformation screening baseline in NewsLens India (`src/ml/train.py`).

---

## 2. File Verification & Checksums

| File | Exact Records | Size (Bytes) | SHA-256 Checksum |
|---|---|---|---|
| `train.tsv` | 10,240 | 2,418,434 | `a4256f0c6519a12a98a6cb3f242579851c9f3b8719f3f6c3ddcee1ef3aec1daa` |
| `valid.tsv` | 1,284 | 302,840 | `6c06cd41e97f4ac8b179b458258dce53564f11498caded73844d052e78fd47fe` |
| `test.tsv` | 1,267 | 302,401 | `2e627fd51adae210237bfa0f0b26e08cd1c3fdfb2c760a42e50a7c346860d0dc` |
| `README` | Description | 1,711 | `0b7b415501cae615293268a105cfc258f3e98bb0c71cdd15d2c1de7422cfefdf` |
| `LICENSE` | MIT License | 1,090 | `fdd1db5004d897911bd708b66c5f5d044d7b1df1e6d90b73311866b8e991f3fc` |

---

## 3. Schema Definition (14 Columns)
Each `.tsv` file is tab-separated with no header row and contains 14 columns:
1. `id`: JSON statement ID
2. `label`: Rating label (`pants-fire`, `false`, `barely-true`, `half-true`, `mostly-true`, `true`)
3. `statement`: The text of the claim being fact-checked
4. `subject`: Topic/subject of the statement
5. `speaker`: Speaker/politician who made the statement
6. `speaker_job_title`: Speaker job title
7. `state_info`: State info
8. `party_affiliation`: Political party affiliation
9. `barely_true_counts`: Historical count of barely-true claims by this speaker
10. `false_counts`: Historical count of false claims by this speaker
11. `half_true_counts`: Historical count of half-true claims by this speaker
12. `mostly_true_counts`: Historical count of mostly-true claims by this speaker
13. `pants_on_fire_counts`: Historical count of pants-on-fire claims by this speaker
14. `context`: The venue/medium (e.g. speech, interview, tweet)

In the binary screening model (`src/ml/train.py`), claims are mapped:
- `pants-fire`, `false`, `barely-true` -> `0` (False / Misleading)
- `half-true`, `mostly-true`, `true` -> `1` (True / Nuanced)
