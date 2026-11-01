"""Backend configuration and environment settings for NewsLens India."""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "NewsLens India API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # External Provider Credentials & Quota Governance
    NEWSDATA_ENABLED: bool = bool(
        os.environ.get("NEWSDATA_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    NEWSDATA_API_KEY: Optional[str] = os.environ.get("NEWSDATA_API_KEY", None)
    NEWSDATA_DAILY_BUDGET: int = int(os.environ.get("NEWSDATA_DAILY_BUDGET", "50"))
    NEWSDATA_15MIN_BUDGET: int = int(os.environ.get("NEWSDATA_15MIN_BUDGET", "10"))
    NEWSDATA_MIN_REFRESH_INTERVAL: float = float(
        os.environ.get("NEWSDATA_MIN_REFRESH_INTERVAL", "60.0")
    )
    NEWSDATA_MAX_PAGES: int = int(os.environ.get("NEWSDATA_MAX_PAGES", "2"))

    # Database and Data paths - respect environment overrides for test isolation
    DB_PATH: str = os.environ.get("NEWSLENS_DB_PATH", "data/newslens.db")
    FACT_CHECKS_PATH: str = os.environ.get("NEWSLENS_FACT_CHECKS_PATH", "data/fact_checks.json")
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


settings = Settings()
