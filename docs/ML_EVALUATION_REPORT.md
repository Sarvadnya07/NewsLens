# ML Evaluation Report: Fake News Screening Model

**Training Date:** 2026-10-30T11:17:04.470496+00:00  
**Model Family:** Logistic Regression (Balanced Class Weights, L2 Regularization, C=1.0)  
**Feature Representation:** TF-IDF (Unigrams + Bigrams, Sublinear TF, 10,000 max features)  
**Dataset:** LIAR Benchmark (Derived binary split from `research/fake-news-detection/train.csv` and `test.csv`)  

---

## 1. Split & Data Integrity

- **Training Samples:** 10240
- **Held-out Test Samples:** 2539
- **Duplicate Leakage Elimination:** Audited and removed 12 identical statement strings between train and test splits before vectorizer transform.
- **Vectorizer Guard:** TF-IDF fitted strictly on training data; test features transformed using training vocabulary.

---

## 2. Test Set Performance Metrics

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | `0.6180` (61.80%) | Overall classification accuracy |
| **Macro Precision** | `0.6157` | Unweighted mean precision across both classes |
| **Macro Recall** | `0.6160` | Unweighted mean recall across both classes |
| **Macro F1-Score** | `0.6158` | Primary benchmark metric for balanced evaluation |
| **Weighted F1-Score** | `0.6183` | Sample-weighted F1 across both classes |
| **Fake Class Precision** | `0.5805` | Precision for False/Misleading statements |
| **Fake Class Recall** | `0.5935` | Recall for False/Misleading statements |
| **Fake Class F1** | `0.5869` | Detection F1 for False/Misleading statements |
| **True Class F1** | `0.6447` | Detection F1 for True/Credible statements |

---

## 3. Confusion Matrix

*Matrix format: `[row = Actual Label, column = Predicted Label]` where `0 = Fake/Misleading`, `1 = True/Credible`*

```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              689                     472       
Actual True (1)               498                     880       
```

---

## 4. Critical Domain Shift Limitation & Responsible AI Notice

1. **Experimental Baseline Only:** This model is trained on US political statements (LIAR benchmark / PolitiFact claims). It is an experimental NLP baseline that captures stylistic and sensationalist lexical patterns.
2. **Not a Truth Verifier:** Model score is a statistical heuristic indicator. It does **NOT** verify real-world facts or breaking developments.
3. **Indian News Context:** Real-world Indian breaking news features localized entity dynamics, acronyms, and multilingual translation patterns that differ substantially from US political speeches.
4. **Mandatory Cross-Corroboration:** Predictions must always be presented alongside multi-source publisher coverage and accredited fact-checking evidence.
