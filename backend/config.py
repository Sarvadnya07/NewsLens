"""Backend configuration and environment settings for NewsLens India."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "NewsLens India API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database and Data paths
    DB_PATH: str = "data/newslens.db"
    FACT_CHECKS_PATH: str = "data/fact_checks.json"
    MODEL_CLASSIFIER_PATH: str = "models/classifier.joblib"
    MODEL_VECTORIZER_PATH: str = "models/tfidf_vectorizer.joblib"
    EVALUATION_METRICS_PATH: str = "models/evaluation_metrics.json"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
