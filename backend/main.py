"""FastAPI application entry point for NewsLens India API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.errors import (
    NewsLensAPIException,
    api_exception_handler,
    unhandled_exception_handler,
)
from backend.api.routes import (
    analysis,
    articles,
    coverage,
    dashboard,
    evidence,
    health,
    ingestion,
    methodology,
)
from backend.config import settings


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    app.add_exception_handler(NewsLensAPIException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Register API v1 Routers
    api_prefix = settings.API_V1_STR
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(articles.router, prefix=api_prefix)
    app.include_router(analysis.router, prefix=api_prefix)
    app.include_router(evidence.router, prefix=api_prefix)
    app.include_router(coverage.router, prefix=api_prefix)
    app.include_router(ingestion.router, prefix=api_prefix)
    app.include_router(methodology.router, prefix=api_prefix)

    return app


app = create_app()
