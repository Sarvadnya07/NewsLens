"""RFC 9457 Problem Details error contract for the NewsLens India API.

Every failure - application, framework validation, HTTP, provider, database or
unexpected - is returned through one machine-readable shape:

    Content-Type: application/problem+json

    {
      "type": "urn:newslens:problem:validation-error",
      "title": "Request validation failed",
      "status": 422,
      "detail": "One or more request fields are invalid.",
      "instance": "/api/v1/analysis",
      "code": "VALIDATION_ERROR",
      "request_id": "6f1c0f1e9d2b4c7a",
      "errors": [{"field": "body.text", "message": "...", "code": "string_too_short"}]
    }

This module is intentionally self-contained (models, sanitizer, taxonomy and
handlers) so the public error contract cannot drift with unrelated modules.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_TYPE_NAMESPACE = "urn:newslens:problem:"
PROBLEM_MEDIA_TYPE = "application/problem+json"
REQUEST_ID_HEADER = "X-Request-ID"

_SECRET_QUERY = re.compile(r"((?:key|api-key|apikey|token|access-key)=)([^&\s]+)", re.IGNORECASE)
_SECRET_BEARER = re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE)


class ProblemFieldError(BaseModel):
    """A single field-level validation failure inside a Problem Details body."""

    field: str = Field(..., description="Dotted location of the offending field")
    message: str = Field(..., description="Human readable explanation")
    code: Optional[str] = Field(None, description="Machine readable validation code")


class ProblemDetails(BaseModel):
    """RFC 9457 Problem Details body returned for every API error.

    ``type`` is a stable URN from the ``urn:newslens:problem:`` namespace and is
    never null; ``code`` carries the stable application error code used by clients
    for control flow.
    """

    type: str = Field(..., description="Stable problem type URI (never null)")
    title: str = Field(..., description="Short, human readable summary")
    status: int = Field(..., description="HTTP status code of the failure")
    detail: Optional[str] = Field(
        None, description="Human readable explanation for this occurrence"
    )
    instance: Optional[str] = Field(None, description="Request path the problem relates to")
    code: str = Field(..., description="Stable application error code")
    request_id: Optional[str] = Field(None, description="Correlation identifier for this request")
    errors: Optional[List[ProblemFieldError]] = Field(
        None, description="Field-level validation failures, when applicable"
    )


# Stable taxonomy: code -> (title, default HTTP status, problem type slug).
# Codes are part of the public contract; never rename an existing code.
ERROR_TAXONOMY: Dict[str, tuple[str, int, str]] = {
    "VALIDATION_ERROR": ("Request validation failed", 422, "validation-error"),
    "EMPTY_INPUT": ("Request body is empty", 422, "empty-input"),
    "BAD_REQUEST": ("Malformed request", 400, "bad-request"),
    "UNAUTHORIZED": ("Authentication required", 401, "unauthorized"),
    "FORBIDDEN": ("Insufficient privileges", 403, "forbidden"),
    "NOT_FOUND": ("Resource not found", 404, "not-found"),
    "ARTICLE_NOT_FOUND": ("Article not found", 404, "not-found"),
    "PROVIDER_NOT_FOUND": ("Provider not found", 404, "not-found"),
    "CONFLICT": ("Request conflicts with current state", 409, "conflict"),
    "UNPROCESSABLE_ENTITY": ("Request could not be processed", 422, "unprocessable-entity"),
    "RATE_LIMITED": ("Too many requests", 429, "rate-limited"),
    "PROVIDER_QUOTA_EXCEEDED": ("Provider quota exhausted", 429, "provider-quota-exceeded"),
    "PROVIDER_NOT_CONFIGURED": ("Provider not configured", 503, "provider-not-configured"),
    "PROVIDER_AUTH_FAILED": ("Provider rejected the credentials", 502, "provider-auth-failed"),
    "PROVIDER_TIMEOUT": ("Provider timed out", 504, "provider-timeout"),
    "PROVIDER_UNAVAILABLE": ("Provider unavailable", 502, "provider-unavailable"),
    "PROVIDER_NOT_IMPLEMENTED": ("Provider not implemented", 501, "provider-not-implemented"),
    "DATABASE_ERROR": ("Database error", 500, "database-error"),
    "INTERNAL_ERROR": ("Internal server error", 500, "internal-error"),
    "SERVICE_UNAVAILABLE": ("Service unavailable", 503, "service-unavailable"),
}

# Backwards compatible mapping of code -> fully qualified problem type URI.
ERROR_TYPES: Dict[str, str] = {
    code: f"{PROBLEM_TYPE_NAMESPACE}{slug}" for code, (_, _, slug) in ERROR_TAXONOMY.items()
}

_STATUS_TO_CODE: Dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    501: "PROVIDER_NOT_IMPLEMENTED",
    502: "PROVIDER_UNAVAILABLE",
    503: "SERVICE_UNAVAILABLE",
    504: "PROVIDER_TIMEOUT",
}


def sanitize_text(text: str) -> str:
    """Strips credential-bearing fragments from messages before publication."""
    if not text:
        return ""
    return _SECRET_BEARER.sub(r"\1[REDACTED]", _SECRET_QUERY.sub(r"\1[REDACTED]", text))


def problem_type_for(code: str, status_code: int = 500) -> str:
    """Returns the stable problem type URI for an application error code."""
    if code in ERROR_TYPES:
        return ERROR_TYPES[code]
    fallback = _STATUS_TO_CODE.get(status_code)
    if fallback:
        return ERROR_TYPES[fallback]
    return ERROR_TYPES["INTERNAL_ERROR"] if status_code >= 500 else ERROR_TYPES["BAD_REQUEST"]


def title_for(code: str, status_code: int) -> str:
    """Returns the stable human readable title for a problem code."""
    spec = ERROR_TAXONOMY.get(code)
    if spec:
        return spec[0]
    fallback = _STATUS_TO_CODE.get(status_code)
    if fallback:
        return ERROR_TAXONOMY[fallback][0]
    return "Request failed"


def code_for_status(status_code: int) -> str:
    """Maps a bare HTTP status onto a stable application error code."""
    return _STATUS_TO_CODE.get(status_code) or (
        "INTERNAL_ERROR" if status_code >= 500 else "BAD_REQUEST"
    )


def request_id_of(request: Request) -> Optional[str]:
    """Correlation identifier attached by the request context middleware."""
    value = getattr(getattr(request, "state", None), "request_id", None)
    return str(value) if value else None


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    return sanitize_text(str(value))


def _field_errors(raw: Any) -> Optional[List[ProblemFieldError]]:
    """Normalises detail payloads into field-level problem entries."""
    if not isinstance(raw, list):
        return None
    errors: List[ProblemFieldError] = []
    for item in raw:
        if isinstance(item, dict):
            field = str(item.get("field") or item.get("loc") or "request")
            message = _clean(item.get("message") or item.get("msg") or "Invalid value")
            errors.append(
                ProblemFieldError(
                    field=field,
                    message=message or "Invalid value",
                    code=_clean(item.get("code") or item.get("type")),
                )
            )
        else:
            errors.append(
                ProblemFieldError(
                    field="request",
                    message=_clean(item) or "Invalid value",
                    code="invalid_field",
                )
            )
    return errors or None


def problem_response(
    request: Request,
    *,
    code: str,
    status_code: int,
    detail: Optional[str] = None,
    errors: Any = None,
    headers: Optional[Dict[str, str]] = None,
) -> JSONResponse:
    """Builds a Problem Details JSON response with the current request id."""
    body = ProblemDetails(
        type=problem_type_for(code, status_code),
        title=title_for(code, status_code),
        status=status_code,
        detail=_clean(detail),
        instance=request.url.path,
        code=code,
        request_id=request_id_of(request),
        errors=_field_errors(errors),
    ).model_dump(exclude_none=True)

    response_headers = {"Content-Type": f"{PROBLEM_MEDIA_TYPE}; charset=utf-8"}
    if headers:
        response_headers.update(headers)
    if status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        response_headers.setdefault("Retry-After", "60")

    return JSONResponse(status_code=status_code, content=body, headers=response_headers)


class NewsLensAPIException(Exception):
    """Raised by application code to return a stable, structured problem response.

    The HTTP status code must match the failure semantics, not merely the presence
    of an error payload.
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
        error_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.error_type = error_type or problem_type_for(code, status_code)
        self.headers = headers
        super().__init__(message)


async def api_exception_handler(request: Request, exc: NewsLensAPIException) -> JSONResponse:
    """Handles application-raised exceptions using the problem contract."""
    headers = dict(exc.headers or {})
    errors = None

    if isinstance(exc.details, dict):
        errors = exc.details.get("errors")
        retry_after = exc.details.get("retry_after_seconds")
        if retry_after is not None:
            headers.setdefault("Retry-After", str(int(max(float(retry_after), 1))))
    else:
        errors = exc.details

    return problem_response(
        request,
        code=exc.code,
        status_code=exc.status_code,
        detail=exc.message,
        errors=errors,
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles framework HTTPExceptions (404s, 405s, dependency errors)."""
    detail = exc.detail if isinstance(exc.detail, str) else None
    code = code_for_status(exc.status_code)
    if exc.status_code == status.HTTP_404_NOT_FOUND and detail is None:
        detail = "The requested resource does not exist."
    return problem_response(
        request,
        code=code,
        status_code=exc.status_code,
        detail=detail,
        headers=dict(exc.headers or {}),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normalises Pydantic/FastAPI 422 responses into the problem contract.

    Submitted values are intentionally not echoed back to avoid leaking secrets.
    """
    errors: List[Dict[str, Any]] = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ())]
        errors.append(
            {
                "field": ".".join(loc) or "request",
                "message": err.get("msg") or "Invalid value",
                "code": err.get("type"),
            }
        )

    return problem_response(
        request,
        code="VALIDATION_ERROR",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="One or more request fields are invalid.",
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Safety net for unexpected failures.

    Logs the real failure internally (with correlation id) and returns a generic
    problem body so implementation details never leak to clients.
    """
    logger.exception(
        "Unhandled server error [request_id=%s] %s %s: %s",
        request_id_of(request) or "-",
        request.method,
        request.url.path,
        sanitize_text(str(exc)),
    )

    return problem_response(
        request,
        code="INTERNAL_ERROR",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected internal server error occurred.",
    )
