"""FastAPI dependency injection provider for service singletons."""

import hmac
import os
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException, Request, status

from backend.config import settings
from src.services.integration_service import IntegrationManager
from src.services.news_service import NewsLensService


def verify_admin_access(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> bool:
    """Enforces authorization for administrative operations.

    In production mode (APP_ENV == 'production') or when explicitly enabled
    (REQUIRE_ADMIN_AUTH_IN_DEV == True), requires a non-empty ADMIN_API_KEY
    and matching X-Admin-Key header.
    In development mode without explicit auth requirement, permits requests for local developer UX.
    """
    is_production = settings.APP_ENV.lower() == "production"
    requires_auth = is_production or settings.REQUIRE_ADMIN_AUTH_IN_DEV

    if not requires_auth:
        return True

    configured_key = settings.ADMIN_API_KEY
    if not configured_key or not str(configured_key).strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Administrative access is not configured for this environment.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not x_admin_key or not hmac.compare_digest(x_admin_key.strip(), configured_key.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid administrative authorization key (X-Admin-Key).",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return True


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
