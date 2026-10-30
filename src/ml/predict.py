"""Inference module for ML-based Fake News Screening in NewsLens India.

Loads verified Joblib artifacts and provides:
- Clean preprocessing
- Prediction class (Credible vs Misleading/Suspect)
- Probabilistic confidence score
- Prominent uncertainty warning context
"""

import os
import joblib
import logging
from typing import Dict, Any, Optional

from src.preprocessing.cleaner import clean_text

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = "models"
VECTORIZER_PATH = os.path.join(ARTIFACTS_DIR, "tfidf_vectorizer.joblib")
CLASSIFIER_PATH = os.path.join(ARTIFACTS_DIR, "classifier.joblib")


class FakeNewsScreeningModel:
    """Safe inference wrapper for TF-IDF + Logistic Regression fake-news classifier."""

    def __init__(
        self,
        vectorizer_path: str = VECTORIZER_PATH,
        classifier_path: str = CLASSIFIER_PATH
    ):
        self.vectorizer_path = vectorizer_path
        self.classifier_path = classifier_path
        self.vectorizer = None
        self.classifier = None
        self._load_artifacts()

    def _load_artifacts(self):
        if not os.path.exists(self.vectorizer_path) or not os.path.exists(self.classifier_path):
            logger.warning("Model artifacts not found at %s and %s", self.vectorizer_path, self.classifier_path)
            return

        try:
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
        - label: 'Credible/Plausible' or 'Misleading/Suspect'
        - raw_label: 1 or 0
        - confidence: float between 0.0 and 1.0
        - prob_fake: probability that text exhibits misleading linguistic features
        - prob_true: probability that text exhibits credible linguistic features
        - uncertainty_note: mandatory disclaimer on statistical limitations
        """
        if not self.is_ready:
            return {
                "status": "error",
                "error": "Model artifacts not loaded. Please train the model first.",
                "label": "Unknown",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "cleaned_text": "",
                "uncertainty_note": "Model not available."
            }

        if not text or not isinstance(text, str) or not text.strip():
            return {
                "status": "empty_input",
                "error": "Input text is empty.",
                "label": "Undetermined",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "cleaned_text": "",
                "uncertainty_note": "Please provide a valid headline or article text."
            }

        cleaned = clean_text(text)
        if len(cleaned.split()) < 2:
            return {
                "status": "short_input",
                "error": "Input text is too short for reliable linguistic screening.",
                "label": "Undetermined",
                "confidence": 0.0,
                "prob_fake": 0.0,
                "prob_true": 0.0,
                "cleaned_text": cleaned,
                "uncertainty_note": "Input text has fewer than 2 recognizable words."
            }

        X = self.vectorizer.transform([cleaned])
        proba = self.classifier.predict_proba(X)[0]
        # proba[0] = False/Fake, proba[1] = True/Credible
        prob_fake = float(proba[0])
        prob_true = float(proba[1])

        pred_class = int(self.classifier.predict(X)[0])
        label = "Credible / Plausible" if pred_class == 1 else "Suspect / Potentially Misleading"
        confidence = prob_true if pred_class == 1 else prob_fake

        # Explain uncertainty when probability is close to decision boundary
        boundary_margin = abs(prob_true - prob_fake)
        is_uncertain = boundary_margin < 0.15

        uncertainty_note = (
            "Note: This score is a statistical language pattern screening heuristic (trained on LIAR benchmark). "
            "It does NOT verify real-world facts or breaking developments. "
            "Always consult primary news sources and accredited fact-checking agencies."
        )
        if is_uncertain:
            uncertainty_note = (
                "Caution: Prediction is near the decision threshold (high uncertainty). "
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
            "uncertainty_note": uncertainty_note
        }
