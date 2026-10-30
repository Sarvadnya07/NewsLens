"""Model training pipeline for Fake News Screening in NewsLens India.

- Loads LIAR benchmark dataset from research/fake-news-detection/train.csv & test.csv
- Checks and documents duplicate leakage
- Applies clean text preprocessing
- Fits TF-IDF vectorizer exclusively on the training split
- Fits Logistic Regression baseline with cross-validation
- Evaluates Accuracy, Precision, Recall, Macro-F1, Weighted-F1, and Confusion Matrix on held-out test split
- Saves verified Joblib artifacts to models/
- Generates reproducible evaluation report in docs/
"""

import json
import logging
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from src.preprocessing.cleaner import clean_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models"
DOCS_DIR = "docs"


def load_and_prepare_data(train_csv_path: str, test_csv_path: str):
    """Loads CSV files, normalizes boolean labels, and removes duplicate leakage."""
    logger.info("Loading training data from %s", train_csv_path)
    train_df = pd.read_csv(train_csv_path)
    test_df = pd.read_csv(test_csv_path)

    # In LIAR binary split: True = Credible/True, False = Fake/Misleading
    train_df = train_df.rename(columns={"Statement": "statement", "Label": "label"})
    test_df = test_df.rename(columns={"Statement": "statement", "Label": "label"})

    # Drop missing statements
    train_df = train_df.dropna(subset=["statement", "label"]).copy()
    test_df = test_df.dropna(subset=["statement", "label"]).copy()

    # Map labels to integer: 1 = True (credible), 0 = False (fake/misleading)
    def to_binary(val):
        if isinstance(val, bool):
            return 1 if val else 0
        s = str(val).strip().lower()
        if s in ("true", "1", "t"):
            return 1
        elif s in ("false", "0", "f"):
            return 0
        return np.nan

    train_df["target"] = train_df["label"].apply(to_binary)
    test_df["target"] = test_df["label"].apply(to_binary)

    train_df = train_df.dropna(subset=["target"]).copy()
    test_df = test_df.dropna(subset=["target"]).copy()
    train_df["target"] = train_df["target"].astype(int)
    test_df["target"] = test_df["target"].astype(int)

    # Preprocess text
    logger.info("Cleaning statements...")
    train_df["cleaned"] = train_df["statement"].apply(clean_text)
    test_df["cleaned"] = test_df["statement"].apply(clean_text)

    # Filter out empty cleaned strings
    train_df = train_df[train_df["cleaned"].str.len() > 3].copy()
    test_df = test_df[test_df["cleaned"].str.len() > 3].copy()

    # Check for train-test duplicate leakage
    train_texts = set(train_df["cleaned"])
    leak_mask = test_df["cleaned"].isin(train_texts)
    num_leaks = int(leak_mask.sum())
    if num_leaks > 0:
        logger.warning(
            "Detected %d duplicate statements in test split leaking from train! Removing from test split.",
            num_leaks,
        )
        test_df = test_df[~leak_mask].copy()

    logger.info(
        "Prepared Train: %d records, Test: %d records (leaks removed: %d)",
        len(train_df),
        len(test_df),
        num_leaks,
    )
    return train_df, test_df, num_leaks


def train_and_evaluate(
    train_csv: str = "research/fake-news-detection/train.csv",
    test_csv: str = "research/fake-news-detection/test.csv",
):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    train_df, test_df, num_leaks = load_and_prepare_data(train_csv, test_csv)

    # Build TF-IDF Vectorizer fitted ONLY on training split
    logger.info("Fitting TF-IDF vectorizer on training split...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True)
    X_train = vectorizer.fit_transform(train_df["cleaned"])
    y_train = train_df["target"].values

    X_test = vectorizer.transform(test_df["cleaned"])
    y_test = test_df["target"].values

    # Train Logistic Regression Baseline
    logger.info("Training Logistic Regression classifier...")
    classifier = LogisticRegression(
        C=1.0, solver="lbfgs", max_iter=1000, class_weight="balanced", random_state=42
    )
    classifier.fit(X_train, y_train)

    # Evaluate on held-out test split
    logger.info("Evaluating on held-out test split...")
    y_pred = classifier.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_pred))
    precision_macro = float(precision_score(y_test, y_pred, average="macro"))
    recall_macro = float(recall_score(y_test, y_pred, average="macro"))
    f1_macro = float(f1_score(y_test, y_pred, average="macro"))
    f1_weighted = float(f1_score(y_test, y_pred, average="weighted"))

    precision_fake = float(precision_score(y_test, y_pred, pos_label=0))
    recall_fake = float(recall_score(y_test, y_pred, pos_label=0))
    f1_fake = float(f1_score(y_test, y_pred, pos_label=0))

    precision_true = float(precision_score(y_test, y_pred, pos_label=1))
    recall_true = float(recall_score(y_test, y_pred, pos_label=1))
    f1_true = float(f1_score(y_test, y_pred, pos_label=1))

    # Confusion matrix: index 0 = Actual False, index 1 = Actual True
    # Column 0 = Predicted False, Column 1 = Predicted True
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
    clf_report = classification_report(
        y_test,
        y_pred,
        labels=[0, 1],
        target_names=["Fake/Misleading (0)", "True/Credible (1)"],
        output_dict=True,
    )

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(train_df)),
        "test_samples": int(len(test_df)),
        "duplicate_leaks_removed": num_leaks,
        "accuracy": accuracy,
        "macro_precision": precision_macro,
        "macro_recall": recall_macro,
        "macro_f1": f1_macro,
        "weighted_f1": f1_weighted,
        "class_ordering": [0, 1],
        "class_labels": ["Fake/Misleading (0)", "True/Credible (1)"],
        "fake_class_metrics": {"precision": precision_fake, "recall": recall_fake, "f1": f1_fake},
        "true_class_metrics": {"precision": precision_true, "recall": recall_true, "f1": f1_true},
        "confusion_matrix": cm,
        "classification_report": clf_report,
    }

    # Persist artifacts with joblib
    vectorizer_path = os.path.join(ARTIFACTS_DIR, "tfidf_vectorizer.joblib")
    classifier_path = os.path.join(ARTIFACTS_DIR, "classifier.joblib")
    metrics_path = os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json")

    logger.info("Saving vectorizer to %s", vectorizer_path)
    joblib.dump(vectorizer, vectorizer_path)

    logger.info("Saving classifier to %s", classifier_path)
    joblib.dump(classifier, classifier_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Generate Markdown Report in docs/
    report_md_path = os.path.join(DOCS_DIR, "ML_EVALUATION_REPORT.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(f"""# ML Evaluation Report: Fake News Screening Model

**Training Date:** {metrics["timestamp"]}
**Model Family:** Logistic Regression (Balanced Class Weights, L2 Regularization, C=1.0)
**Feature Representation:** TF-IDF (Unigrams + Bigrams, Sublinear TF, 10,000 max features)
**Dataset:** LIAR Benchmark (Derived binary split from `research/fake-news-detection/train.csv` and `test.csv`)

---

## 1. Split & Data Integrity

- **Training Samples:** {metrics["train_samples"]}
- **Held-out Test Samples:** {metrics["test_samples"]}
- **Duplicate Leakage Elimination:** Audited and removed {metrics["duplicate_leaks_removed"]} identical statement strings between train and test splits before vectorizer transform.
- **Vectorizer Guard:** TF-IDF fitted strictly on training data; test features transformed using training vocabulary.

---

## 2. Test Set Performance Metrics

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | `{metrics["accuracy"]:.4f}` ({metrics["accuracy"] * 100:.2f}%) | Overall classification accuracy |
| **Macro Precision** | `{metrics["macro_precision"]:.4f}` | Unweighted mean precision across both classes |
| **Macro Recall** | `{metrics["macro_recall"]:.4f}` | Unweighted mean recall across both classes |
| **Macro F1-Score** | `{metrics["macro_f1"]:.4f}` | Primary benchmark metric for balanced evaluation |
| **Weighted F1-Score** | `{metrics["weighted_f1"]:.4f}` | Sample-weighted F1 across both classes |
| **Fake Class Precision** | `{metrics["fake_class_metrics"]["precision"]:.4f}` | Precision for False/Misleading statements |
| **Fake Class Recall** | `{metrics["fake_class_metrics"]["recall"]:.4f}` | Recall for False/Misleading statements |
| **Fake Class F1** | `{metrics["fake_class_metrics"]["f1"]:.4f}` | Detection F1 for False/Misleading statements |
| **True Class F1** | `{metrics["true_class_metrics"]["f1"]:.4f}` | Detection F1 for True/Credible statements |

---

## 3. Confusion Matrix

*Matrix format: `[row = Actual Label, column = Predicted Label]` where `0 = Fake/Misleading`, `1 = True/Credible`*

```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              {cm[0][0]:<10}              {cm[0][1]:<10}
Actual True (1)               {cm[1][0]:<10}              {cm[1][1]:<10}
```

---

## 4. Critical Domain Shift Limitation & Responsible AI Notice

1. **Experimental Baseline Only:** This model is trained on US political statements (LIAR benchmark / PolitiFact claims). It is an experimental NLP baseline that captures stylistic and sensationalist lexical patterns.
2. **Not a Truth Verifier:** Model score is a statistical heuristic indicator. It does **NOT** verify real-world facts or breaking developments.
3. **Indian News Context:** Real-world Indian breaking news features localized entity dynamics, acronyms, and multilingual translation patterns that differ substantially from US political speeches.
4. **Mandatory Cross-Corroboration:** Predictions must always be presented alongside multi-source publisher coverage and accredited fact-checking evidence.
""")

    logger.info(
        "Training and evaluation completed successfully. Report generated at %s", report_md_path
    )
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
