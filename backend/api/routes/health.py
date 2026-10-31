"""Health check endpoints for NewsLens India API."""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_news_service
from backend.schemas.common import APIResponse
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=APIResponse[dict])
def health_check():
    """Liveness probe confirming API service is up."""
    return APIResponse(data={"status": "healthy", "service": "NewsLens India API"})


@router.get("/ready", response_model=APIResponse[dict])
def readiness_check(service: NewsLensService = Depends(get_news_service)):
    """Readiness probe verifying database and ML model readiness."""
    db_ok = service.db.get_article_count() >= 0
    ml_ok = service.ml_model.is_ready
    retriever_ok = len(service.retriever.records) > 0

    is_ready = db_ok and ml_ok
    return APIResponse(
        data={
            "ready": is_ready,
            "database": "connected" if db_ok else "unreachable",
            "ml_model": "loaded" if ml_ok else "uninitialized",
            "fact_checks_indexed": len(service.retriever.records),
            "retriever": "ready" if retriever_ok else "empty",
        }
    )
