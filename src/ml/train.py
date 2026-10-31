"""Model training and evaluation pipeline for Fake News Screening in NewsLens India.

Reads the canonical LIAR benchmark dataset directly from original TSV files:
    * Training: data/liar/train.tsv (10,269 records)
    * Validation: data/liar/valid.tsv (1,284 records)
    * Official Test: data/liar/test.tsv (1,283 records)

Uses csv.QUOTE_NONE parsing to prevent standard RFC 4180 CSV quote absorbers from
collapsing physical lines into multiline strings.

- Detects and documents duplicate statement collisions with the training partition
- Trains TF-IDF and Logistic Regression baseline exclusively on the training partition
- Evaluates diagnostic metrics on the validation partition
- Benchmarks final performance exclusively on the untouched official test partition
- Persists native Joblib artifacts to models/
- Generates reproducible evaluation report in docs/ML_EVALUATION_REPORT.md
"""

import csv
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Tuple

import joblib
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

# Class names describe LIAR label groups, not factual verdicts. Class 1 contains
# half-true claims, so calling it "true" would overstate what the model measures.
LOWER_VERACITY_LABEL = "Lower-veracity group (0)"
HIGHER_VERACITY_LABEL = "Higher-veracity group (1)"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models"
DOCS_DIR = "docs"

LIAR_COLUMNS = [
    "id",
    "label",
    "statement",
    "subjects",
    "speaker",
    "job_title",
    "state_info",
    "party_affiliation",
    "barely_true_count",
    "false_count",
    "half_true_count",
    "mostly_true_count",
    "pants_on_fire_count",
    "context",
]


def map_binary_label(val: str) -> int:
    """Maps the 6 original LIAR labels into binary classes:
    Class 0: Lower-veracity label group (pants-fire, false, barely-true).
    Class 1: Higher-veracity label group (half-true, mostly-true, true).
    """
    clean_val = str(val).strip().lower()
    if clean_val in ("half-true", "mostly-true", "true", "1", "t"):
        return 1
    return 0


def load_canonical_tsv(path: str) -> pd.DataFrame:
    """Reads a canonical LIAR TSV file using csv.QUOTE_NONE to ensure embedded quotes
    do not absorb subsequent records.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Canonical LIAR TSV file not found: {path}")

    df = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=LIAR_COLUMNS,
        quoting=csv.QUOTE_NONE,
        encoding="utf-8",
        dtype=str,
    )
    # Ensure all strings are non-null and strip leading/trailing whitespace
    for col in ["id", "label", "statement"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def load_and_prepare_dataset(
    train_tsv_path: str = "data/liar/train.tsv",
    valid_tsv_path: str = "data/liar/valid.tsv",
    test_tsv_path: str = "data/liar/test.tsv",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    """Loads and preprocesses the 3 canonical LIAR partitions directly from original TSVs."""
    logger.info(
        "Loading canonical TSVs: train=%s, valid=%s, test=%s",
        train_tsv_path,
        valid_tsv_path,
        test_tsv_path,
    )

    train_df = load_canonical_tsv(train_tsv_path)
    valid_df = load_canonical_tsv(valid_tsv_path)
    test_df = load_canonical_tsv(test_tsv_path)

    raw_counts = {
        "train_raw": int(len(train_df)),
        "valid_raw": int(len(valid_df)),
        "test_raw": int(len(test_df)),
    }

    # Verify canonical column schema
    for name, df in [("train", train_df), ("valid", valid_df), ("test", test_df)]:
        if df.shape[1] != 14:
            raise ValueError(f"Partition {name} does not match 14 columns: got {df.shape[1]}")

    # Map labels and preprocess text
    for df in [train_df, valid_df, test_df]:
        df["target"] = df["label"].apply(map_binary_label)
        df["cleaned"] = df["statement"].apply(clean_text)

    # Filter empty statements if any
    train_df = train_df[train_df["cleaned"].str.len() > 3].copy()
    train_texts = set(train_df["cleaned"])

    # Audit duplicate statement collisions with the training set
    test_leak_mask = test_df["cleaned"].isin(train_texts)
    valid_leak_mask = valid_df["cleaned"].isin(train_texts)

    num_test_leaks = int(test_leak_mask.sum())
    num_valid_leaks = int(valid_leak_mask.sum())

    logger.warning(
        "Detected duplicate statement collisions with train: Test=%d, Valid=%d",
        num_test_leaks,
        num_valid_leaks,
    )

    clean_test_df = test_df[(test_df["cleaned"].str.len() > 3) & (~test_leak_mask)].copy()
    clean_valid_df = valid_df[(valid_df["cleaned"].str.len() > 3) & (~valid_leak_mask)].copy()

    leak_stats = {
        **raw_counts,
        "test_duplicates_removed": num_test_leaks,
        "valid_duplicates_removed": num_valid_leaks,
        "total_duplicates_removed": num_test_leaks + num_valid_leaks,
        "train_prepared": int(len(train_df)),
        "valid_prepared": int(len(clean_valid_df)),
        "test_prepared": int(len(clean_test_df)),
    }

    logger.info(
        "Prepared Canonical Partitions: Train=%d, Valid=%d (purged: %d), Official Test=%d (purged: %d)",
        len(train_df),
        len(clean_valid_df),
        num_valid_leaks,
        len(clean_test_df),
        num_test_leaks,
    )
    return train_df, clean_valid_df, clean_test_df, leak_stats


def train_and_evaluate(
    train_tsv: str = "data/liar/train.tsv",
    valid_tsv: str = "data/liar/valid.tsv",
    test_tsv: str = "data/liar/test.tsv",
):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)

    train_df, valid_df, test_df, split_stats = load_and_prepare_dataset(
        train_tsv, valid_tsv, test_tsv
    )

    # Fit TF-IDF Vectorizer STRICTLY on the training partition
    logger.info("Fitting TF-IDF vectorizer exclusively on training partition...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000, sublinear_tf=True)
    X_train = vectorizer.fit_transform(train_df["cleaned"])
    y_train = train_df["target"].values

    X_valid = vectorizer.transform(valid_df["cleaned"])
    y_valid = valid_df["target"].values

    X_test = vectorizer.transform(test_df["cleaned"])
    y_test = test_df["target"].values

    # Train Logistic Regression model exclusively on train
    logger.info("Training Logistic Regression classifier on training partition...")
    classifier = LogisticRegression(
        C=1.0, solver="lbfgs", max_iter=1000, class_weight="balanced", random_state=42
    )
    classifier.fit(X_train, y_train)

    # Validation Set Diagnostic Evaluation
    y_val_pred = classifier.predict(X_valid)
    valid_accuracy = float(accuracy_score(y_valid, y_val_pred))
    valid_macro_f1 = float(f1_score(y_valid, y_val_pred, average="macro"))
    cm_valid = confusion_matrix(y_valid, y_val_pred, labels=[0, 1]).tolist()

    # Official Test Set Evaluation (Final Untouched Benchmark)
    logger.info("Evaluating classifier on untouched official test partition...")
    y_test_pred = classifier.predict(X_test)

    accuracy = float(accuracy_score(y_test, y_test_pred))
    precision_macro = float(precision_score(y_test, y_test_pred, average="macro"))
    recall_macro = float(recall_score(y_test, y_test_pred, average="macro"))
    f1_macro = float(f1_score(y_test, y_test_pred, average="macro"))
    f1_weighted = float(f1_score(y_test, y_test_pred, average="weighted"))

    precision_fake = float(precision_score(y_test, y_test_pred, pos_label=0))
    recall_fake = float(recall_score(y_test, y_test_pred, pos_label=0))
    f1_fake = float(f1_score(y_test, y_test_pred, pos_label=0))

    precision_true = float(precision_score(y_test, y_test_pred, pos_label=1))
    recall_true = float(recall_score(y_test, y_test_pred, pos_label=1))
    f1_true = float(f1_score(y_test, y_test_pred, pos_label=1))

    # Confusion matrix on official test set:
    # Row 0 = Actual False (0), Row 1 = Actual True (1)
    # Col 0 = Pred False (0), Col 1 = Pred True (1)
    cm_test = confusion_matrix(y_test, y_test_pred, labels=[0, 1]).tolist()
    clf_report = classification_report(
        y_test,
        y_test_pred,
        labels=[0, 1],
        target_names=[LOWER_VERACITY_LABEL, HIGHER_VERACITY_LABEL],
        output_dict=True,
    )

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "methodology": "Canonical LIAR TSV Ingestion (QUOTE_NONE) with 3-Way Partitions",
        "train_samples": split_stats["train_prepared"],
        "valid_samples": split_stats["valid_prepared"],
        "official_test_samples": split_stats["test_prepared"],
        "duplicate_leaks_removed": {
            "test_partition": split_stats["test_duplicates_removed"],
            "validation_partition": split_stats["valid_duplicates_removed"],
            "total": split_stats["total_duplicates_removed"],
        },
        "accuracy": accuracy,
        "macro_precision": precision_macro,
        "macro_recall": recall_macro,
        "macro_f1": f1_macro,
        "weighted_f1": f1_weighted,
        "class_ordering": [0, 1],
        "class_labels": [LOWER_VERACITY_LABEL, HIGHER_VERACITY_LABEL],
        "class_semantics": (
            "Class 0 = pants-fire/false/barely-true; Class 1 = half-true/mostly-true/true. "
            "These are LIAR label groups, not factual verdicts about Indian news."
        ),
        "fake_class_metrics": {
            "precision": precision_fake,
            "recall": recall_fake,
            "f1": f1_fake,
        },
        "true_class_metrics": {
            "precision": precision_true,
            "recall": recall_true,
            "f1": f1_true,
        },
        "confusion_matrix": cm_test,
        "classification_report": clf_report,
        "validation_set_diagnostic": {
            "samples": split_stats["valid_prepared"],
            "accuracy": valid_accuracy,
            "macro_f1": valid_macro_f1,
            "confusion_matrix": cm_valid,
        },
    }

    # Save artifacts
    vectorizer_path = os.path.join(ARTIFACTS_DIR, "tfidf_vectorizer.joblib")
    classifier_path = os.path.join(ARTIFACTS_DIR, "classifier.joblib")
    metrics_path = os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json")

    logger.info("Saving vectorizer to %s", vectorizer_path)
    joblib.dump(vectorizer, vectorizer_path)

    logger.info("Saving classifier to %s", classifier_path)
    joblib.dump(classifier, classifier_path)

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Generate updated documentation
    report_md_path = os.path.join(DOCS_DIR, "ML_EVALUATION_REPORT.md")
    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(f"""# ML Evaluation Report: Fake News Screening Model

**Training Date:** {metrics["timestamp"]}
**Model Family:** Logistic Regression (Balanced Class Weights, L2 Regularization, C=1.0)
**Feature Representation:** TF-IDF (Unigrams + Bigrams, Sublinear TF, 10,000 max features)
**Dataset:** Canonical LIAR Benchmark (Parsed directly from original TSVs via `csv.QUOTE_NONE`)

---

## 1. Split Integrity & Partition Accounting

The canonical LIAR benchmark (Wang, ACL 2017) comprises distinct training, validation, and test partitions.
Previous pipelines utilized a derived `train.csv` (10,240 rows) and `test.csv` (2,551 rows) where unclosed quotation marks had caused standard CSV parsers to absorb 29 training records and 16 test records.

In this corrected pipeline, the original TSV files are ingested directly using `csv.QUOTE_NONE`:
- **Training Partition (`train.tsv`):** {split_stats["train_raw"]} raw statements -> **{metrics["train_samples"]}** prepared.
- **Validation Partition (`valid.tsv`, diagnostic only):** {split_stats["valid_raw"]} raw statements -> **{metrics["valid_samples"]}** prepared (removed {split_stats["valid_duplicates_removed"]} duplicate statements colliding with train).
- **Official Test Partition (`test.tsv`, final untouched evaluation):** {split_stats["test_raw"]} raw statements -> **{metrics["official_test_samples"]}** prepared (removed {split_stats["test_duplicates_removed"]} duplicate statements colliding with train).
- **Leakage Policy:** Feature extraction (TF-IDF vocabulary and IDF weights) and classifier weights are learned exclusively on the training partition ({metrics["train_samples"]} statements). Neither validation nor test observations influence model fitting.

---

## 2. Official Test Set Performance Metrics (N = {metrics["official_test_samples"]})

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | `{metrics["accuracy"]:.4f}` ({metrics["accuracy"] * 100:.2f}%) | Overall classification accuracy on official test |
| **Macro Precision** | `{metrics["macro_precision"]:.4f}` | Unweighted mean precision across classes |
| **Macro Recall** | `{metrics["macro_recall"]:.4f}` | Unweighted mean recall across classes |
| **Macro F1-Score** | `{metrics["macro_f1"]:.4f}` | Primary balanced benchmark metric |
| **Weighted F1-Score** | `{metrics["weighted_f1"]:.4f}` | Sample-weighted F1 across classes |
| **Lower-Veracity Group Precision (class 0)** | `{metrics["fake_class_metrics"]["precision"]:.4f}` | Precision for pants-fire / false / barely-true claims |
| **Lower-Veracity Group Recall (class 0)** | `{metrics["fake_class_metrics"]["recall"]:.4f}` | Recall for pants-fire / false / barely-true claims |
| **Lower-Veracity Group F1 (class 0)** | `{metrics["fake_class_metrics"]["f1"]:.4f}` | F1 for pants-fire / false / barely-true claims |
| **Higher-Veracity Group Precision (class 1)** | `{metrics["true_class_metrics"]["precision"]:.4f}` | Precision for half-true / mostly-true / true claims |
| **Higher-Veracity Group Recall (class 1)** | `{metrics["true_class_metrics"]["recall"]:.4f}` | Recall for half-true / mostly-true / true claims |
| **Higher-Veracity Group F1 (class 1)** | `{metrics["true_class_metrics"]["f1"]:.4f}` | F1 for half-true / mostly-true / true claims |

---

## 3. Official Test Confusion Matrix

*Matrix format: `[row = Actual label group, column = Predicted label group]` where `0 = lower-veracity LIAR group` and `1 = higher-veracity LIAR group`. These groups are not factual verdicts.*

```
                        Predicted lower (0)    Predicted higher (1)
Actual lower (0)               {cm_test[0][0]:<14}           {cm_test[0][1]}
Actual higher (1)              {cm_test[1][0]:<14}           {cm_test[1][1]}
```

- Total evaluation samples: {cm_test[0][0]} + {cm_test[0][1]} + {cm_test[1][0]} + {cm_test[1][1]} = {sum(sum(row) for row in cm_test)}.
- Verified Accuracy: ({cm_test[0][0]} + {cm_test[1][1]}) / {sum(sum(row) for row in cm_test)} = {metrics["accuracy"]:.4f}.

---

## 4. Validation Set Diagnostic Check (N = {metrics["valid_samples"]})

- **Validation Accuracy:** `{valid_accuracy:.4f}` ({valid_accuracy * 100:.2f}%)
- **Validation Macro F1:** `{valid_macro_f1:.4f}`
- **Validation Confusion Matrix:**
```
                      Predicted False (0)    Predicted True (1)
Actual False (0)              {cm_valid[0][0]:<10}              {cm_valid[0][1]}
Actual True (1)               {cm_valid[1][0]:<10}              {cm_valid[1][1]}
```

---

## 5. Critical Domain Shift Limitation & Responsible AI Notice

1. **Experimental Linguistic Screening Only:** This model captures stylistic, linguistic, and sensationalist phrasing patterns from US political statements (LIAR benchmark).
2. **Not Ground-Truth Verification:** A statistical screening score is not fact-checking and does not confirm whether a breaking news claim is true in the real world.
3. **Domain Shift in Indian News:** Indian political discourse, local government initiatives, regional names, and vernacular translations differ significantly from US political discourse.
4. **Mandatory Corroboration:** NewsLens India pairs screening scores with live RSS publisher corroboration and accredited fact-checking retrieval (PIB Fact Check, BOOM Live, Alt News).
""")

    logger.info("Training and evaluation completed successfully.")
    return metrics


if __name__ == "__main__":
    train_and_evaluate()
