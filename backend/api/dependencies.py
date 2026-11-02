"""FastAPI dependency injection provider for service singletons.

Administrative authorization is NOT implemented here: it lives in exactly one
place, ``backend.main.verify_admin_access``, so a route cannot accidentally be
gated by a stale copy of the policy.
"""

import os
from functools import lru_cache

from backend.config import settings
from src.services.integration_service import IntegrationManager
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


@lru_cache()
def get_integration_manager() -> IntegrationManager:
    """Provides a singleton instance of IntegrationManager bound to the central news service DB."""
    service = get_news_service()
    return IntegrationManager(
        db=service.db,
        rss=service.rss,
        gdelt=service.gdelt,
        newsdata=service.newsdata,
    )
