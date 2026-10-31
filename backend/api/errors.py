"""Consistent API Error handling and status mapping."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse

from backend.schemas.common import APIErrorDetail, APIErrorResponse

logger = logging.getLogger(__name__)


class NewsLensAPIException(Exception):
    def __init__(
        self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details=None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


async def api_exception_handler(request: Request, exc: NewsLensAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIErrorResponse(
            success=False,
            error=APIErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            ),
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIErrorResponse(
            success=False,
            error=APIErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
            ),
        ).model_dump(),
    )
