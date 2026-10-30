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
            logger.info("Loaded vectorizer and classifier artifacts successfully.")
        except Exception as e:
            logger.error("Failed to load model artifacts: %s", str(e))
            self.vectorizer = None
            self.classifier = None

    @property
    def is_ready(self) -> bool:
        return self.vectorizer is not None and self.classifier is not None

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

        cleaned = clean_text(text)
        tokens = cleaned.split()
        if len(tokens) < 2:
            return {
                "status": "short_input",
                "error": "Input text is too short for reliable linguistic screening.",
                "label": "Undetermined",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "is_uncertain": True,
                "cleaned_text": cleaned,
                "uncertainty_note": "Input text contains fewer than 2 recognizable words.",
            }

        X = self.vectorizer.transform([cleaned])
        proba = self.classifier.predict_proba(X)[0]
        # Class 0 = Fake/Misleading, Class 1 = True/Credible
        prob_fake = float(proba[0])
        prob_true = float(proba[1])

        pred_class = int(self.classifier.predict(X)[0])
        label = "Credible / Plausible" if pred_class == 1 else "Suspect / Potentially Misleading"
        confidence = prob_true if pred_class == 1 else prob_fake

        # Explain uncertainty when probability is close to decision boundary
        boundary_margin = abs(prob_true - prob_fake)
        is_uncertain = boundary_margin < 0.15

        uncertainty_note = (
            "Model Advisory: This score reflects statistical linguistic patterns learned from the LIAR benchmark. "
            "It is NOT a factual truth determination and has NOT verified real-world events. "
            "Because this model was trained on political claims, Indian news contexts may introduce domain shift. "
            "Always inspect multi-source publisher coverage and accredited fact-checking evidence."
        )
        if is_uncertain:
            uncertainty_note = (
                "High Uncertainty: The prediction is close to the 50/50 decision threshold. "
                + uncertainty_note
            )

        return {
            "status": "success",
            "label": label,
            "raw_class": pred_class,
            "confidence": round(confidence, 4),
            "prob_fake": round(prob_fake, 4),
            "prob_true": round(prob_true, 4),
            "is_uncertain": is_uncertain,
            "cleaned_text": cleaned,
            "uncertainty_note": uncertainty_note,
        }
