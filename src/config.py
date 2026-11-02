"""Neutral configuration and secret-redaction helpers for NewsLens India.

This module deliberately has no dependency on ``backend``: the domain engine
(``src/*``) must be importable without the web layer. ``backend.config``
re-exports these objects for the API boundary, so both names resolve to the
same singleton.

Includes automatic secret redaction for safe logging and status reporting.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "NewsLens India API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False

    # ------------------------------------------------------------------
    # Existing Ingestion: NewsData.io
    # ------------------------------------------------------------------
    NEWSDATA_ENABLED: bool = True
    NEWSDATA_API_KEY: Optional[str] = None
    NEWSDATA_DAILY_BUDGET: int = 50
    NEWSDATA_15MIN_BUDGET: int = 10
    NEWSDATA_MIN_REFRESH_INTERVAL: float = 60.0
    NEWSDATA_MAX_PAGES: int = 2

    # ------------------------------------------------------------------
    # Existing Ingestion: GDELT 2.0 DOC API
    # ------------------------------------------------------------------
    GDELT_ENABLED: bool = True

    # ------------------------------------------------------------------
    # Additional Aggregator: Currents API
    # ------------------------------------------------------------------
    CURRENTS_ENABLED: bool = False
    CURRENTS_API_KEY: Optional[str] = None
    CURRENTS_DAILY_BUDGET: int = 250
    CURRENTS_15MIN_BUDGET: int = 25
    CURRENTS_MIN_REFRESH_INTERVAL: float = 60.0
    CURRENTS_DEFAULT_MAX_PAGES: int = 1

    # ------------------------------------------------------------------
    # Fact-Check: Google Fact Check Tools API
    # ------------------------------------------------------------------
    GOOGLE_FACTCHECK_ENABLED: bool = False
    GOOGLE_FACTCHECK_API_KEY: Optional[str] = None
    GOOGLE_FACTCHECK_DAILY_BUDGET: int = 500
    GOOGLE_FACTCHECK_MIN_REFRESH_INTERVAL: float = 5.0

    # ------------------------------------------------------------------
    # First-Party Publisher: The Guardian Open Platform
    # ------------------------------------------------------------------
    GUARDIAN_ENABLED: bool = False
    GUARDIAN_API_KEY: Optional[str] = None
    GUARDIAN_DAILY_BUDGET: int = 500
    GUARDIAN_15MIN_BUDGET: int = 50
    GUARDIAN_MIN_REFRESH_INTERVAL: float = 5.0
    GUARDIAN_DEFAULT_MAX_PAGES: int = 2

    # ------------------------------------------------------------------
    # Official & Regional RSS Feeds
    # ------------------------------------------------------------------
    PIB_ENABLED: bool = True
    ABP_RSS_ENABLED: bool = True
    AMAR_UJALA_RSS_ENABLED: bool = True

    # ------------------------------------------------------------------
    # Backlog Integrations
    # ------------------------------------------------------------------
    NYT_ENABLED: bool = False
    NYT_API_KEY: Optional[str] = None

    BRAVE_ENABLED: bool = False
    BRAVE_API_KEY: Optional[str] = None

    # ------------------------------------------------------------------
    # Global HTTP & Resilience Controls
    # ------------------------------------------------------------------
    INTEGRATION_REQUEST_TIMEOUT: float = 20.0
    INTEGRATION_LOG_SECRETS: bool = False
    # Provider verification evidence older than this is no longer "operational".
    PROVIDER_STATUS_STALENESS_HOURS: float = 24.0

    # ------------------------------------------------------------------
    # Security & Administration
    # ------------------------------------------------------------------
    # When APP_ENV=production, administrative actions (/test, /refresh)
    # require a valid X-Admin-Key matching ADMIN_API_KEY.
    # In development mode, loopback/local requests are permitted for developer UX.
    ADMIN_API_KEY: Optional[str] = None
    REQUIRE_ADMIN_AUTH_IN_DEV: bool = False
    REQUIRE_ADMIN_AUTH_FOR_INGESTION: bool = False
    ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV: bool = True
    ADMIN_RATE_LIMIT_PER_MINUTE: int = 30

    # ------------------------------------------------------------------
    # Database and Data Paths
    # ------------------------------------------------------------------
    DB_PATH: str = os.environ.get("NEWSLENS_DB_PATH", "data/newslens.db")
    FACT_CHECKS_PATH: str = os.environ.get("NEWSLENS_FACT_CHECKS_PATH", "data/fact_checks.json")
    MODEL_CLASSIFIER_PATH: str = "models/classifier.joblib"
    MODEL_VECTORIZER_PATH: str = "models/tfidf_vectorizer.joblib"
    EVALUATION_METRICS_PATH: str = "models/evaluation_metrics.json"

    # ------------------------------------------------------------------
    # CORS settings
    # ------------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()


def redact_secret(val: Optional[str]) -> str:
    """Masks secret keys for safe logging and API telemetry."""
    if not val:
        return "[Not Configured]"
    cleaned = str(val).strip()
    if len(cleaned) <= 6:
        return "***"
    return f"{cleaned[:3]}...{cleaned[-3:]}"


def sanitize_text(text: str) -> str:
    """Strips secrets and sensitive parameters from logs or error messages."""
    if not text:
        return ""
    # Strip API keys in query params (key=SECRET -> key=[REDACTED])
    clean = re.sub(
        r"((?:key|api-key|apikey|token|access-key)=)([^&\s]+)",
        r"\1[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )
    # Strip Bearer tokens
    clean = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1[REDACTED]", clean, flags=re.IGNORECASE)
    return clean
