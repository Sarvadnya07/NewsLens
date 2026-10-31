# ML Evaluation Report: Fake News Screening Model

**Training Date:** 2026-10-30T19:20:07.665666+00:00
**Model Family:** Logistic Regression (Balanced Class Weights, L2 Regularization, C=1.0)
**Feature Representation:** TF-IDF (Unigrams + Bigrams, Sublinear TF, 10,000 max features)
**Dataset:** Canonical LIAR Benchmark (Parsed directly from original TSVs via `csv.QUOTE_NONE`)

---

## 1. Split Integrity & Partition Accounting

The canonical LIAR benchmark (Wang, ACL 2017) comprises distinct training, validation, and test partitions.
Previous pipelines utilized a derived `train.csv` (10,240 rows) and `test.csv` (2,551 rows) where unclosed quotation marks had caused standard CSV parsers to absorb 29 training records and 16 test records.

In this corrected pipeline, the original TSV files are ingested directly using `csv.QUOTE_NONE`:
- **Training Partition (`train.tsv`):** 10269 raw statements -> **10269** prepared.
- **Validation Partition (`valid.tsv`, diagnostic only):** 1284 raw statements -> **1277** prepared (removed 7 duplicate statements colliding with train).
- **Official Test Partition (`test.tsv`, final untouched evaluation):** 1283 raw statements -> **1278** prepared (removed 5 duplicate statements colliding with train).
- **Leakage Policy:** Feature extraction (TF-IDF vocabulary and IDF weights) and classifier weights are learned exclusively on the training partition (10269 statements). Neither validation nor test observations influence model fitting.

---

## 2. Official Test Set Performance Metrics (N = 1278)

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | `0.6307` (63.07%) | Overall classification accuracy on official test |
| **Macro Precision** | `0.6259` | Unweighted mean precision across classes |
| **Macro Recall** | `0.6272` | Unweighted mean recall across classes |
| **Macro F1-Score** | `0.6262` | Primary balanced benchmark metric |
| **Weighted F1-Score** | `0.6316` | Sample-weighted F1 across classes |
| **Fake Class Precision** | `0.5702` | Precision for False/Misleading statements |
| **Fake Class Recall** | `0.6011` | Recall for False/Misleading statements |
| **Fake Class F1** | `0.5852` | Detection F1 for False/Misleading statements |
| **True Class Precision** | `0.6816` | Precision for True/Credible statements |
| **True Class Recall** | `0.6533` | Recall for True/Credible statements |
| **True Class F1** | `0.6671` | Detection F1 for True/Credible statements |

---

## 3. Official Test Confusion Matrix

*Matrix format: `[row = Actual Label, column = Predicted Label]` where `0 = Fake/Misleading (Lower veracity)`, `1 = True/Credible (Higher veracity)`*

```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              333                     221
Actual True (1)               251                     473
```

- Total evaluation samples: 333 + 221 + 251 + 473 = 1278.
- Verified Accuracy: (333 + 473) / 1278 = 0.6307.

---

## 4. Validation Set Diagnostic Check (N = 1277)

- **Validation Accuracy:** `0.6147` (61.47%)
- **Validation Macro F1:** `0.6141`
- **Validation Confusion Matrix:**
```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              366                     244
Actual True (1)               248                     419
```

---

## 5. Critical Domain Shift Limitation & Responsible AI Notice

1. **Experimental Linguistic Screening Only:** This model captures stylistic, linguistic, and sensationalist phrasing patterns from US political statements (LIAR benchmark).
2. **Not Ground-Truth Verification:** A statistical screening score is not fact-checking and does not confirm whether a breaking news claim is true in the real world.
3. **Domain Shift in Indian News:** Indian political discourse, local government initiatives, regional names, and vernacular translations differ significantly from US political discourse.
4. **Mandatory Corroboration:** NewsLens India pairs screening scores with live RSS publisher corroboration and accredited fact-checking retrieval (PIB Fact Check, BOOM Live, Alt News).
