"""Statistical evaluation pipeline for the NewsLens India ML screening model.

Provides:
    * Bootstrap confidence intervals for test-set metrics
    * Calibration diagnostics (Brier score, expected calibration error)
    * Abstention / selective prediction analysis with coverage-risk curves

All functions are deterministic given a ``seed`` and are independent of the
Streamlit UI so they can be unit-tested in isolation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default abstention threshold used by the existing UI (margin < 0.15)
DEFAULT_ABSTENTION_MARGIN = 0.15


@dataclass
class BootstrapCI:
    """Bootstrap uncertainty estimate for a single metric."""

    metric_name: str
    point_estimate: float
    lower_bound: float
    upper_bound: float
    confidence: float
    n_resamples: int
    resampling_method: str = "stratified_by_query"

    def to_dict(self) -> Dict[str, float]:
        return {
            "metric": self.metric_name,
            "estimate": round(self.point_estimate, 4),
            "ci_lower": round(self.lower_bound, 4),
            "ci_upper": round(self.upper_bound, 4),
            "confidence": self.confidence,
            "n_resamples": self.n_resamples,
            "resampling_method": self.resampling_method,
        }


def _log2(x: float) -> float:
    import math

    return math.log2(x)


def _brier_score(y_true: np.ndarray, y_prob: np.ndarray, pos_class: int = 1) -> float:
    """Compute the Brier score for binary predictions.

    Brier = mean((p - y)^2).  p is the predicted probability for the
    positive class, y is the binary ground-truth label (0/1).
    """
    if len(y_true) == 0:
        return 0.0
    y_bin = (np.asarray(y_true) == pos_class).astype(float)
    p = np.clip(np.asarray(y_prob), 0.0, 1.0)
    return float(np.mean((p - y_bin) ** 2))
def _roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute ROC AUC using the Mann-Whitney U statistic."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    if len(np.unique(y_true)) < 2:
        return 0.5
    n_pos = float(np.sum(y_true == 1))
    n_neg = float(np.sum(y_true == 0))
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(y_score)
    ranks = np.empty(len(y_score), dtype=float)
    ranks[order] = np.arange(1, len(y_score) + 1)
    i = 0
    while i < len(y_score):
        j = i
        while j < len(y_score) - 1 and y_score[order[j]] == y_score[order[j + 1]]:
            j += 1
        if j > i:
            avg_rank = (ranks[order[i]] + ranks[order[j]]) / 2.0
            ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = np.sum(ranks[y_true == 1])
    auc = (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def _reliability_bins(
    y_true: np.ndarray, y_score: np.ndarray, n_bins: int = 10
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute per-bin confidence and accuracy for a reliability diagram."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    if len(y_true) == 0:
        return np.array([]), np.array([])
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2.0
    bin_conf = np.zeros(n_bins)
    bin_acc = np.zeros(n_bins)
    for b in range(n_bins):
        mask = (y_score >= bins[b]) & (y_score < bins[b + 1])
        if b == n_bins - 1:
            mask = (y_score >= bins[b]) & (y_score <= bins[b + 1])
        if np.any(mask):
            bin_conf[b] = float(np.mean(y_score[mask]))
            bin_acc[b] = float(np.mean(y_true[mask]))
        else:
            bin_conf[b] = 0.0
            bin_acc[b] = 0.0
    return bin_centers, bin_acc


def compute_metrics_stratified(
    y_true: np.ndarray,
    y_score: np.ndarray,
    y_pred: np.ndarray,
    labels: Optional[Dict[str, int]] = None,
) -> Dict[str, float]:
    """Compute a full stratified metric report without bootstrapping."""
    if labels is None:
        labels = {0: "negative", 1: "positive"}
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = np.asarray(y_pred)

    n_pos = float(np.sum(y_true == 1))
    n_neg = float(np.sum(y_true == 0))
    n_total = float(len(y_true))

    tp = float(np.sum((y_true == 1) & (y_pred == 1)))
    tn = float(np.sum((y_true == 0) & (y_pred == 0)))
    fp = float(np.sum((y_true == 0) & (y_pred == 1)))
    fn = float(np.sum((y_true == 1) & (y_pred == 0)))

    acc = float(np.mean(y_true == y_pred))
    sens = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    spec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = float((sens + spec) / 2.0)

    prec_0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    rec_0 = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1_0 = 2 * prec_0 * rec_0 / (prec_0 + rec_0) if (prec_0 + rec_0) > 0 else 0.0

    prec_1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec_1 = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_1 = 2 * prec_1 * rec_1 / (prec_1 + rec_1) if (prec_1 + rec_1) > 0 else 0.0

    macro_prec = (prec_0 + prec_1) / 2.0
    macro_rec = (rec_0 + rec_1) / 2.0
    macro_f1 = (f1_0 + f1_1) / 2.0
    weighted_f1 = (f1_0 * n_neg + f1_1 * n_pos) / n_total if n_total > 0 else 0.0
    auc = _roc_auc(y_true, y_score)
    brier = _brier_score(y_true, y_score)

    ece = 0.0
    if n_total > 0:
        n_bins = 10
        for b in range(n_bins):
            lo = b / n_bins
            hi = (b + 1) / n_bins
            mask = (y_score >= lo) & (y_score < hi)
            if b == n_bins - 1:
                mask = (y_score >= lo) & (y_score <= hi)
            if np.any(mask):
                conf = np.mean(y_score[mask])
                acc_bin = np.mean(y_true[mask])
                ece += (np.sum(mask) / n_total) * abs(conf - acc_bin)

    return {
        "accuracy": acc,
        "balanced_accuracy": balanced_acc,
        "sensitivity": sens,
        "specificity": spec,
        "class_0_precision": prec_0,
        "class_0_recall": rec_0,
        "class_0_f1": f1_0,
        "class_1_precision": prec_1,
        "class_1_recall": rec_1,
        "class_1_f1": f1_1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "roc_auc": auc,
        "brier_score": brier,
        "expected_calibration_error": ece,
        "n_samples": n_total,
        "n_pos": n_pos,
        "n_neg": n_neg,
    }

def bootstrap_metric_ci(
    y_true: np.ndarray,
    y_score: np.ndarray,
    y_pred: np.ndarray,
    metric_functions: Dict[str, callable],
    labels: Optional[Dict[str, int]] = None,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = 42,
) -> Dict[str, BootstrapCI]:
    """Compute bootstrap confidence intervals for multiple metrics.

    Resamples evaluation examples (stratified on the true label) and
    computes the point estimate and bootstrap CI for each metric.
    """
    if labels is None:
        labels = {0: "negative", 1: "positive"}
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    y_pred = np.asarray(y_pred)

    n = len(y_true)
    rng = np.random.default_rng(seed)

    # Stratified bootstrap: sample within each class
    pos_idx = np.where(y_true == 1)[0]
    neg_idx = np.where(y_true == 0)[0]

    per_query_scores: Dict[str, List[float]] = {
        name: [] for name in metric_functions
    }

    for _ in range(n_resamples):
        pos_sample = rng.choice(pos_idx, size=len(pos_idx), replace=True)
        neg_sample = rng.choice(neg_idx, size=len(neg_idx), replace=True)
        idx = np.concatenate([pos_sample, neg_sample])
        y_t = y_true[idx]
        y_s = y_score[idx]
        y_p = y_pred[idx]

        for name, fn in metric_functions.items():
            val = fn(y_t, y_s, y_p, labels)
            per_query_scores[name].append(val)

    results: Dict[str, BootstrapCI] = {}
    for name, scores in per_query_scores.items():
        if not scores:
            results[name] = BootstrapCI(
                metric_name=name,
                point_estimate=0.0,
                lower_bound=0.0,
                upper_bound=0.0,
                confidence=confidence,
                n_resamples=n_resamples,
            )
            continue
        arr = np.array(scores, dtype=float)
        point_est = float(np.mean(arr))
        boot_sorted = np.sort(arr)
        alpha = 1.0 - confidence
        lo = int(n_resamples * alpha / 2)
        hi = int(n_resamples * (1.0 - alpha / 2))
        results[name] = BootstrapCI(
            metric_name=name,
            point_estimate=point_est,
            lower_bound=float(boot_sorted[lo]),
            upper_bound=float(boot_sorted[hi]),
            confidence=confidence,
            n_resamples=n_resamples,
        )
    return results

def abstention_analysis(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    margins: np.ndarray,
    coverage_points: int = 20,
    margin_step: float = 0.02,
) -> Dict[str, any]:
    """Evaluate selective prediction / abstention across thresholds.

    Computes coverage, selective risk, and per-class precision/recall as
    abstention thresholds vary.  This is the core metric suite for deciding
    the operating point of an uncertainty-aware screening model.

    Parameters
    ----------
    y_true : np.ndarray (n,)
        Ground-truth binary labels.
    y_pred : np.ndarray (n,)
        Model's binary predictions (0 or 1).
    margins : np.ndarray (n,)
        Absolute decision margin |P(1) - P(0)| for each example.  Higher
        values imply more confident predictions.
    coverage_points : int
        Number of threshold levels to evaluate.
    margin_step : float
        Spacing between threshold levels.

    Returns
    -------
    dict
        Keys:
            thresholds : np.ndarray (m,)
            coverage : np.ndarray (m,)
            risk : np.ndarray (m,)
            class_0_precision : np.ndarray (m,)
            class_1_precision : np.ndarray (m,)
            class_0_recall : np.ndarray (m,)
            class_1_recall : np.ndarray (m,)
            margin_step : float
            n_total : int
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    margins_arr = np.asarray(margins)

    thresholds = np.arange(margin_step, 1.0 + 1e-6, margin_step)

    coverage: List[float] = []
    risk: List[float] = []
    class_0_precision: List[float] = []
    class_1_precision: List[float] = []
    class_0_recall: List[float] = []
    class_1_recall: List[float] = []

    n = len(y_true)
    for th in thresholds:
        keep_mask = margins_arr >= th
        reject_mask = ~keep_mask
        cov = float(np.mean(keep_mask))
        coverage.append(cov)

        if np.sum(keep_mask) == 0:
            risk.append(0.0)
            class_0_precision.append(0.0)
            class_1_precision.append(0.0)
            class_0_recall.append(0.0)
            class_1_recall.append(0.0)
            continue

        y_t = y_true[keep_mask]
        y_p = y_pred[keep_mask]

        acc_keep = float(np.mean(y_t == y_p))
        risk.append(1.0 - acc_keep)

        c0 = y_t == 0
        c1 = y_t == 1
        cls0_pred_1 = (y_p == 1) & c0
        cls1_pred_0 = (y_p == 0) & c1

        n_pred_0 = np.sum(y_p == 0)
        n_pred_1 = np.sum(y_p == 1)
        n_c0 = np.sum(c0)
        n_c1 = np.sum(c1)

        p0 = np.sum(cls0_pred_1) / n_pred_0 if n_pred_0 > 0 else 0.0
        p1 = np.sum(cls1_pred_0) / n_pred_1 if n_pred_1 > 0 else 0.0
        r0 = np.sum(cls0_pred_1) / n_c0 if n_c0 > 0 else 0.0
        r1 = np.sum(cls1_pred_0) / n_c1 if n_c1 > 0 else 0.0

        class_0_precision.append(p0)
        class_1_precision.append(p1)
        class_0_recall.append(r0)
        class_1_recall.append(r1)

    return {
        "thresholds": thresholds,
        "coverage": coverage,
        "risk": risk,
        "class_0_precision": class_0_precision,
        "class_1_precision": class_1_precision,
        "class_0_recall": class_0_recall,
        "class_1_recall": class_1_recall,
        "margin_step": margin_step,
        "n_total": n,
    }

def abstention_analysis(
    y_true: np.ndarray,
    y_score: np.ndarray,
    margins: np.ndarray,
    margins_sorted: np.ndarray,
    coverage_points: int = 20,
    margin_step: float = 0.02,
) -> Dict[str, any]:
    """Evaluate selective prediction / abstention across thresholds.

    Computes coverage, selective risk, and per-class precision/recall as
    abstention thresholds vary.  This is the core metric suite for deciding
    the operating point of an uncertainty-aware screening model.
    """
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    margins_arr = np.asarray(margins)
    sorted_margins = np.asarray(margins_sorted)

    thresholds = np.arange(
        margin_step, 1.0 + 1e-6, margin_step
    )

    coverage: List[float] = []
    risk: List[float] = []
    class_0_precision: List[float] = []
    class_1_precision: List[float] = []
    class_0_recall: List[float] = []
    class_1_recall: List[float] = []

    n = len(y_true)
    for th in thresholds:
        keep_mask = margins_arr >= th
        reject_mask = ~keep_mask
        cov = float(np.mean(keep_mask))
        coverage.append(cov)

        if np.sum(keep_mask) == 0:
            risk.append(0.0)
            class_0_precision.append(0.0)
            class_1_precision.append(0.0)
            class_0_recall.append(0.0)
            class_1_recall.append(0.0)
            continue

        y_t_keep = y_true[keep_mask]
        y_p_keep = y_preds[keep_mask]

        # Selective risk: error rate among accepted predictions
        acc_keep = float(np.mean(y_t_keep == y_p_keep))
        risk.append(1.0 - acc_keep)

        # Class-wise performance
        c0 = y_t_keep == 0
        c1 = y_t_keep == 1
        cls0_pred_1 = (y_p_keep == 1) & c0
        cls1_pred_0 = (y_p_keep == 0) & c1

        p0 = np.sum(cls0_pred_1) / np.sum(y_p_keep == 0) if np.sum(y_p_keep == 0) > 0 else 0.0
        p1 = np.sum(cls1_pred_0) / np.sum(y_p_keep == 1) if np.sum(y_p_keep == 1) > 0 else 0.0
        r0 = np.sum(cls0_pred_1) / np.sum(c0) if np.sum(c0) > 0 else 0.0
        r1 = np.sum(cls1_pred_0) / np.sum(c1) if np.sum(c1) > 0 else 0.0

        class_0_precision.append(p0)
        class_1_precision.append(p1)
        class_0_recall.append(r0)
        class_1_recall.append(r1)

    return {
        "thresholds": thresholds,
        "coverage": coverage,
        "risk": risk,
        "class_0_precision": class_0_precision,
        "class_1_precision": class_1_precision,
        "class_0_recall": class_0_recall,
        "class_1_recall": class_1_recall,
        "margin_step": margin_step,
        "n_total": n,
    }

