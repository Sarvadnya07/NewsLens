"""Inference module for ML-based Fake News Screening in NewsLens India.

Loads verified Joblib artifacts and provides:
- Clean preprocessing matching training pipeline
- Prediction class (Credible vs Misleading/Suspect)
- Probabilistic confidence score
- Out-of-domain and language awareness
- Prominent uncertainty and domain-shift warning context
"""

import logging
import os
import warnings
from typing import Any, Dict

import joblib

from src.preprocessing.cleaner import clean_text

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models"
MAX_INPUT_CHARS = 20_000  # hard bound on screening input size (payload limit)
VECTORIZER_PATH = os.path.join(ARTIFACTS_DIR, "tfidf_vectorizer.joblib")
CLASSIFIER_PATH = os.path.join(ARTIFACTS_DIR, "classifier.joblib")


class FakeNewsScreeningModel:
    """Safe inference wrapper for TF-IDF + Logistic Regression fake-news classifier."""

    def __init__(
        self, vectorizer_path: str = VECTORIZER_PATH, classifier_path: str = CLASSIFIER_PATH
    ):
        self.vectorizer_path = vectorizer_path
        self.classifier_path = classifier_path
        self.vectorizer = None
        self.classifier = None
        self._load_artifacts()

    def _load_artifacts(self):
        if not os.path.exists(self.vectorizer_path) or not os.path.exists(self.classifier_path):
            logger.warning(
                "Model artifacts not found at %s and %s", self.vectorizer_path, self.classifier_path
            )
            return

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=DeprecationWarning)
                self.vectorizer = joblib.load(self.vectorizer_path)
                self.classifier = joblib.load(self.classifier_path)
                if self.classifier is not None and not hasattr(self.classifier, "multi_class"):
                    self.classifier.multi_class = "auto"
            logger.info("Loaded vectorizer and classifier artifacts successfully.")
        except Exception as e:
            logger.error("Failed to load model artifacts: %s", str(e))
            self.vectorizer = None
            self.classifier = None

    @property
    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.classifier is not None

    def get_influential_tokens(self, text: str, top_n: int = 5) -> list[tuple[str, str]]:
        """Extracts non-zero features and their input contributions (C_i = x_i * w_i) for the given text."""
        if not self.is_ready:
            return []
        try:
            import numpy as np

            cleaned = clean_text(text)
            vectorizer = self.vectorizer
            classifier = self.classifier
            if vectorizer is None or classifier is None:
                return []
            X = vectorizer.transform([cleaned])
            feature_names = np.array(vectorizer.get_feature_names_out())
            coefs = classifier.coef_[0]
            non_zero_indices = X.nonzero()[1]
            if len(non_zero_indices) == 0:
                return []

            token_weights = []
            for idx in non_zero_indices:
                token = feature_names[idx]
                w = float(coefs[idx])
                x_val = float(X[0, idx])
                # Feature explanation token contribution C_i = x_i * w_i
                contribution = x_val * w
                token_weights.append((token, contribution))

            # Sort by absolute contribution impact |C_i|
            token_weights.sort(key=lambda item: abs(item[1]), reverse=True)
            formatted = []
            for tok, weight in token_weights[:top_n]:
                sign = "+" if weight >= 0 else "-"
                formatted.append((tok.upper(), f"{sign}{abs(weight):.2f}"))
            return formatted
        except Exception as e:
            logger.debug("Failed to extract influential tokens: %s", e)
            return []

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Screens input text. Returns:
        - label: 'Credible / Plausible' or 'Suspect / Potentially Misleading'
        - raw_class: 1 or 0
        - confidence: float between 0.0 and 1.0
        - prob_fake: model score for misleading class
        - prob_true: model score for credible class
        - uncertainty_note: mandatory disclaimer on statistical & domain limitations
        """
        if not self.is_ready:
            return {
                "status": "error",
                "error": "Model artifacts not loaded. Please ensure models are trained.",
                "label": "Unknown",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "is_uncertain": True,
                "cleaned_text": "",
                "uncertainty_note": "Model not available.",
            }

        if not text or not isinstance(text, str) or not text.strip():
            return {
                "status": "empty_input",
                "error": "Input text is empty.",
                "label": "Undetermined",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "is_uncertain": True,
                "cleaned_text": "",
                "uncertainty_note": "Please provide a valid headline or article text.",
            }

        input_truncated = False
        if len(text) > MAX_INPUT_CHARS:
            text = text[:MAX_INPUT_CHARS]
            input_truncated = True
            logger.warning(
                "Screening input exceeded %d characters; using the first %d characters.",
                MAX_INPUT_CHARS,
                MAX_INPUT_CHARS,
            )

        cleaned = clean_text(text)
        tokens = cleaned.split()
        vectorizer = self.vectorizer
        classifier = self.classifier
        if vectorizer is None or classifier is None:
            raise RuntimeError("Screening model artifacts are not loaded")

        if len(tokens) < 2:
            return {
                "status": "short_input",
                "error": "Input text is too short for reliable linguistic screening.",
                "label": "Undetermined",
                "confidence": 0.0,
                "score": 0.0,
                "model_score": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "is_uncertain": True,
                "cleaned_text": cleaned,
                "explanation": "Input text contains fewer than 2 recognizable words.",
                "uncertainty_note": "Input text contains fewer than 2 recognizable words.",
                "influential_tokens": [],
                "tokens": [],
            }

        X = vectorizer.transform([cleaned])
        if X.nnz == 0:
            insufficient_msg = (
                "None of the words in the submitted text overlap with the model's trained vocabulary. "
                "Statistical linguistic screening cannot provide a meaningful veracity indicator. "
                "Model Advisory: This model was trained on the US political LIAR benchmark and does not have calibrated vocabulary for this input. "
                "Always inspect multi-source publisher coverage and accredited fact-checking evidence."
            )
            return {
                "status": "insufficient_signal",
                "label": "Insufficient / No Meaningful Model Signal",
                "raw_class": -1,
                "confidence": 0.5,
                "score": 0.5,
                "model_score": 0.5,
                "prob_fake": 0.5,
                "prob_true": 0.5,
                "is_uncertain": True,
                "cleaned_text": cleaned,
                "explanation": insufficient_msg,
                "uncertainty_note": insufficient_msg,
                "influential_tokens": [],
                "tokens": [],
            }

        proba = classifier.predict_proba(X)[0]
        # Class 0 = lower-veracity LIAR label group, Class 1 = higher-veracity group
        prob_fake = float(proba[0])
        prob_true = float(proba[1])

        pred_class = int(classifier.predict(X)[0])
        label = (
            "Higher-veracity linguistic pattern"
            if pred_class == 1
            else "Lower-veracity linguistic pattern"
        )
        model_score = prob_true if pred_class == 1 else prob_fake

        # Explain uncertainty when probability is close to decision boundary
        boundary_margin = abs(prob_true - prob_fake)
        is_uncertain = boundary_margin < 0.15

        uncertainty_note = (
            "Model Advisory: This score reflects statistical linguistic patterns learned from the US political LIAR benchmark. "
            "It is a heuristic linguistic screening signal, NOT a factual verification, truth determination, or judicial validation. "
            "Because this model was trained on political claims, Indian news contexts introduce substantial domain shift. "
            "Always inspect multi-source publisher coverage and accredited fact-checking evidence."
        )
        if is_uncertain:
            uncertainty_note = (
                "Uncertain / Insufficient Signal: Model output is close to the decision boundary (margin < 0.15). "
                + uncertainty_note
            )
        if input_truncated:
            uncertainty_note = (
                f"Input truncated to the first {MAX_INPUT_CHARS} characters before screening. "
                + uncertainty_note
            )

        influential = self.get_influential_tokens(text, top_n=6)

        return {
            "status": "success",
            "input_truncated": input_truncated,
            "label": label,
            "raw_class": pred_class,
            "confidence": round(model_score, 4),
            "score": round(model_score, 4),
            "model_score": round(model_score, 4),
            "prob_fake": round(prob_fake, 4),
            "prob_true": round(prob_true, 4),
            "is_uncertain": is_uncertain,
            "cleaned_text": cleaned,
            "explanation": uncertainty_note,
            "uncertainty_note": uncertainty_note,
            "influential_tokens": influential,
            "tokens": tokens,
        }
