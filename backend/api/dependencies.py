"""FastAPI dependency injection provider for service singletons."""

import os
from functools import lru_cache

from backend.config import settings
from src.services.news_service import NewsLensService


@lru_cache()
def get_news_service() -> NewsLensService:
    """Provides a singleton instance of NewsLensService bound to configured database and data paths."""
    db_path = os.environ.get("NEWSLENS_DB_PATH", settings.DB_PATH)
    fact_checks_path = os.environ.get("NEWSLENS_FACT_CHECKS_PATH", settings.FACT_CHECKS_PATH)
    return NewsLensService(
        db_path=db_path,
        fact_checks_path=fact_checks_path,
    )
