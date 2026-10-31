"""FastAPI dependency injection provider for service singletons."""

from functools import lru_cache

from backend.config import settings
from src.services.news_service import NewsLensService


@lru_cache()
def get_news_service() -> NewsLensService:
    """Provides a singleton instance of NewsLensService bound to configured database and data paths."""
    return NewsLensService(
        db_path=settings.DB_PATH,
        fact_checks_path=settings.FACT_CHECKS_PATH,
    )
