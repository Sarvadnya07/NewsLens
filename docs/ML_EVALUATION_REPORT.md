# ML Evaluation Report: Fake News Screening Model

**Training Date:** 2026-10-30T10:46:11.007579+00:00  
**Model Family:** Logistic Regression (Balanced Class Weights, L2 Regularization)  
**Feature Representation:** TF-IDF (Unigrams + Bigrams, Sublinear TF, 10,000 features)  
**Dataset:** LIAR Benchmark (train.csv and test.csv from `research/fake-news-detection/`)  

---

## 1. Split & Data Integrity

- **Training Samples:** 10240
- **Held-out Test Samples:** 2539
- **Duplicate Leakage Elimination:** Verified and removed identical statement strings between train and test splits before vectorizer transform.
- **Vectorizer Guard:** TF-IDF fitted strictly on training data; test features transformed using training vocabulary.

---

## 2. Test Set Performance Metrics

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | `0.6180` (61.80%) | Overall classification accuracy |
| **Macro Precision** | `0.6157` | Unweighted mean precision across both classes |
| **Macro Recall** | `0.6160` | Unweighted mean recall across both classes |
| **Macro F1-Score** | `0.6158` | Primary benchmark metric for balanced evaluation |
| **Fake Class F1** | `0.5869` | Specific detection score for False/Misleading statements |

---

## 3. Confusion Matrix

```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              689                     472       
Actual True (1)               498                     880       
```

---

## 4. Key Engineering Takeaways & Limitations

1. **Screening vs Verification:** This model is a statistical heuristic indicator for linguistic patterns. It cannot assess factual truth in real-world breaking news without external multi-source corroboration.
2. **Context Shift:** LIAR consists of political statement claims. Indian breaking news possesses distinct entity dynamics and localized vocabulary, reinforcing the necessity of multi-source RSS/GDELT and BM25 fact-check retrieval.
