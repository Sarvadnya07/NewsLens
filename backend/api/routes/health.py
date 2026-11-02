"""Health check endpoints for NewsLens India API."""

from fastapi import APIRouter, Depends, Response, status

from backend.api.dependencies import get_news_service
from backend.schemas.common import APIResponse
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=APIResponse[dict])
def health_check():
    """Liveness probe confirming API service is up."""
    return APIResponse(data={"status": "healthy", "service": "NewsLens India API"})


@router.get("/ready", response_model=APIResponse[dict])
def readiness_check(
    response: Response,
    service: NewsLensService = Depends(get_news_service),
):
    """Readiness probe: can this instance safely serve traffic?

    Readiness gates only on the dependencies without which core operations are
    broken (datastore reachable, screening model loaded) and answers ``503`` when
    either is unavailable, so an orchestrator can actually take the instance out
    of rotation. The fact-check index is reported but not gating: evidence search
    degrades to an empty result set rather than failing every request.
    """
    db_ok = service.db.ping()
    ml_ok = service.ml_model.is_ready
    fact_checks_indexed = len(service.retriever.records)

    is_ready = db_ok and ml_ok
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return APIResponse(
        data={
            "ready": is_ready,
            "database": "connected" if db_ok else "unreachable",
            "ml_model": "loaded" if ml_ok else "uninitialized",
            "fact_checks_indexed": fact_checks_indexed,
            "retriever": "ready" if fact_checks_indexed > 0 else "empty",
        }
    )
