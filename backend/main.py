"""FastAPI application entry point for NewsLens India API.

Owns the cross-cutting API-boundary concerns: request correlation
(``X-Request-ID``), structured access logging, startup security validation, the
RFC 9457 problem-details error handlers, and their OpenAPI documentation.

Security helpers read ``settings`` defensively (``getattr`` with defaults) so an
older or minimal settings object can never silently disable authorization.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import deque
from contextvars import ContextVar
from typing import Deque, Dict, Optional, Tuple

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from backend.api.errors import (
    NewsLensAPIException,
    ProblemDetails,
    ProblemFieldError,
    api_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from backend.api.routes import (
    analysis,
    articles,
    coverage,
    dashboard,
    evidence,
    health,
    ingestion,
    integrations,
    methodology,
)
from backend.config import settings

REQUEST_ID_HEADER = "X-Request-ID"
_ALLOWED_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")

VALID_APP_ENVS: tuple[str, ...] = ("development", "test", "staging", "production")
MIN_ADMIN_KEY_LENGTH = 16

# Hosts physically local to this interpreter. ``testclient`` is the in-process
# ASGI client: unreachable over a network, and its host cannot be supplied by a
# remote caller.
LOCAL_CLIENT_HOSTS = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1", "localhost", "testclient"})

request_id_context: ContextVar[Optional[str]] = ContextVar("newslens_request_id", default=None)
access_logger = logging.getLogger("backend.api.access")

OPENAPI_TAGS = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Dashboard", "description": "Aggregated operational metrics for the Overview page."},
    {"name": "Articles", "description": "Paginated article queries and manual submissions."},
    {"name": "Analysis", "description": "ML linguistic screening and evidence matching."},
    {"name": "Evidence", "description": "BM25Plus fact-check retrieval."},
    {"name": "Coverage", "description": "Multi-publisher clustering and graph topology."},
    {"name": "Ingestion", "description": "Source status and ingestion triggers."},
    {"name": "Integrations", "description": "Provider registry, diagnostics, and quota telemetry."},
    {"name": "Methodology", "description": "Model, dataset, and evaluation documentation."},
]

_DOCUMENTED_ERROR_RESPONSES = (
    "400",
    "401",
    "403",
    "404",
    "409",
    "422",
    "429",
    "500",
    "503",
    "default",
)


# ---------------------------------------------------------------------------
# Configuration and security policy
# ---------------------------------------------------------------------------


def normalize_app_env(value: Optional[str]) -> str:
    """Returns the canonical environment name, or '' when the value is invalid."""
    env = (value or "").strip().lower()
    return env if env in VALID_APP_ENVS else ""


def resolve_app_env(config=None) -> str:
    """Returns the effective environment, failing closed on unknown values."""
    cfg = config or settings
    raw = getattr(cfg, "APP_ENV", "development")
    return normalize_app_env(raw) or "production"


def is_production(config=None) -> bool:
    """True when the effective environment requires fail-closed authorization."""
    return resolve_app_env(config) == "production"


def admin_api_key() -> str:
    return str(getattr(settings, "ADMIN_API_KEY", None) or "").strip()


def ingestion_enforcement_enabled() -> bool:
    return bool(getattr(settings, "REQUIRE_ADMIN_AUTH_FOR_INGESTION", False))


def validate_security_configuration(config=None) -> None:
    """Validates security-relevant configuration at startup.

    Raises:
        RuntimeError: when the environment name is invalid, the administrative
            credential is unusable, or privileged enforcement is enabled without
            a configured credential.
    """
    cfg = config or settings

    env = normalize_app_env(getattr(cfg, "APP_ENV", None))
    if not env:
        raise RuntimeError(
            f"APP_ENV={getattr(cfg, 'APP_ENV', None)!r} is not a recognised environment. "
            f"Expected one of: {', '.join(VALID_APP_ENVS)}."
        )

    key = str(getattr(cfg, "ADMIN_API_KEY", None) or "").strip()
    if key and len(key) < MIN_ADMIN_KEY_LENGTH:
        raise RuntimeError(
            f"ADMIN_API_KEY must be at least {MIN_ADMIN_KEY_LENGTH} characters long."
        )

    if getattr(cfg, "REQUIRE_ADMIN_AUTH_FOR_INGESTION", False) and not key:
        raise RuntimeError(
            "REQUIRE_ADMIN_AUTH_FOR_INGESTION=true requires ADMIN_API_KEY to be configured. "
            "Refusing to start with unauthenticated privileged endpoints."
        )


def client_host(request: Request) -> str:
    """Transport-level peer host. Forwarding headers are deliberately ignored."""
    client = getattr(request, "client", None)
    return (getattr(client, "host", "") or "").strip().lower()


def verify_admin_access(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> bool:
    """Enforces administrative authorization.

    * Production (or any unrecognised environment): a configured ``ADMIN_API_KEY``
      is mandatory and a matching ``X-Admin-Key`` header is required. Missing
      configuration fails closed with 503.
    * Development/test: unauthenticated calls are allowed only for loopback
      clients while ``ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV`` is true.
      ``REQUIRE_ADMIN_AUTH_IN_DEV=true`` disables the bypass.

    Comparison is constant time; expected and supplied values are never echoed.
    """
    import hmac

    bypass_allowed = (
        not is_production()
        and bool(getattr(settings, "ALLOW_UNAUTHENTICATED_ADMIN_IN_DEV", True))
        and not bool(getattr(settings, "REQUIRE_ADMIN_AUTH_IN_DEV", False))
        and client_host(request) in LOCAL_CLIENT_HOSTS
    )
    if bypass_allowed:
        return True

    configured_key = admin_api_key()
    if not configured_key:
        raise NewsLensAPIException(
            code="SERVICE_UNAVAILABLE",
            message=(
                "Administrative access is not configured for this environment. "
                "Set ADMIN_API_KEY on the server."
            ),
            status_code=503,
            headers={"WWW-Authenticate": "ApiKey"},
        )

    provided = (x_admin_key or "").strip()
    matches = False
    if provided:
        try:
            matches = hmac.compare_digest(provided, configured_key)
        except TypeError:  # non-ASCII input cannot match an ASCII secret
            matches = False

    if not matches:
        raise NewsLensAPIException(
            code="UNAUTHORIZED",
            message="Missing or invalid administrative authorization key (X-Admin-Key).",
            status_code=401,
            details={"authenticated": False, "channel": "header:X-Admin-Key"},
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True


def verify_ingestion_access(
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> bool:
    """Gates ingestion triggers only when administrative enforcement is enabled."""
    if not ingestion_enforcement_enabled():
        return True
    return verify_admin_access(request=request, x_admin_key=x_admin_key)


# ---------------------------------------------------------------------------
# Rate limiting (per process; see docs/API.md)
# ---------------------------------------------------------------------------

_MAX_TRACKED_CLIENTS = 512


class SlidingWindowLimiter:
    """Thread-safe sliding-window counter with bounded memory."""

    def __init__(self, limit: int, window_seconds: float, max_clients: int = _MAX_TRACKED_CLIENTS):
        self.limit = max(int(limit), 1)
        self.window_seconds = float(window_seconds)
        self.max_clients = max(int(max_clients), 1)
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> Tuple[bool, float]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            if key not in self._hits and len(self._hits) >= self.max_clients:
                self._hits.pop(next(iter(self._hits)), None)
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False, max(bucket[0] + self.window_seconds - now, 1.0)
            bucket.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiters: Dict[Tuple[int, float], SlidingWindowLimiter] = {}
_registry_lock = threading.Lock()


def reset_rate_limits() -> None:
    """Clears all limiter state (used by tests and manual operations)."""
    with _registry_lock:
        for limiter in _limiters.values():
            limiter.reset()
        _limiters.clear()


def _get_limiter(limit: int, window_seconds: float) -> SlidingWindowLimiter:
    key = (int(limit), float(window_seconds))
    with _registry_lock:
        limiter = _limiters.get(key)
        if limiter is None:
            limiter = SlidingWindowLimiter(limit=key[0], window_seconds=key[1])
            _limiters[key] = limiter
        return limiter


def enforce_rate_limit(request: Request, scope: str) -> None:
    """Consumes one unit of the privileged budget or raises HTTP 429."""
    limit = max(int(getattr(settings, "ADMIN_RATE_LIMIT_PER_MINUTE", 30) or 1), 1)
    limiter = _get_limiter(limit, 60.0)
    allowed, retry_after = limiter.hit(f"{scope}:{client_host(request) or 'unknown'}")
    if allowed:
        return

    raise NewsLensAPIException(
        code="RATE_LIMITED",
        message=f"Rate limit exceeded for '{scope}' ({limit} requests/minute). Retry shortly.",
        status_code=429,
        details={"retry_after_seconds": round(retry_after, 1), "scope": scope, "limit": limit},
    )


# ---------------------------------------------------------------------------
# Request correlation
# ---------------------------------------------------------------------------


def current_request_id() -> Optional[str]:
    """Returns the correlation id of the request being served, if any."""
    return request_id_context.get()


def resolve_request_id(raw_value: Optional[str]) -> str:
    """Reuses a well-formed inbound identifier, otherwise generates a new one."""
    candidate = (raw_value or "").strip()
    if _ALLOWED_REQUEST_ID.match(candidate):
        return candidate
    return uuid.uuid4().hex


async def request_context_middleware(request: Request, call_next) -> Response:
    """Attaches a request id, times the request, and logs its outcome."""
    request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    token = request_id_context.set(request_id)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started) * 1000
        access_logger.exception(
            "request failed [request_id=%s] %s %s after %.1fms",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    finally:
        request_id_context.reset(token)

    duration_ms = (time.perf_counter() - started) * 1000
    response.headers[REQUEST_ID_HEADER] = request_id

    route = request.scope.get("route")
    route_template = getattr(route, "path", None) or request.url.path
    access_logger.info(
        "request complete [request_id=%s] %s %s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        route_template,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# OpenAPI contract
# ---------------------------------------------------------------------------


def _install_openapi_contract(app: FastAPI) -> None:
    """Publishes the problem-details schema and error responses in OpenAPI."""

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            tags=OPENAPI_TAGS,
            routes=app.routes,
        )

        components = schema.setdefault("components", {}).setdefault("schemas", {})
        components["ProblemDetails"] = ProblemDetails.model_json_schema()
        components["ProblemFieldError"] = ProblemFieldError.model_json_schema()

        problem_body = {
            "description": "RFC 9457 Problem Details",
            "content": {
                "application/problem+json": {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                }
            },
        }

        for operations in schema.get("paths", {}).values():
            for operation in operations.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue
                for code in _DOCUMENTED_ERROR_RESPONSES:
                    operation["responses"].setdefault(code, dict(problem_body))

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def create_app() -> FastAPI:
    """Builds and configures the FastAPI application instance.

    Raises:
        RuntimeError: when security-relevant configuration is invalid.
    """
    validate_security_configuration()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "NewsLens India API. Errors use RFC 9457 Problem Details "
            "(application/problem+json) with a stable `code` and `request_id`."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=OPENAPI_TAGS,
    )

    app.middleware("http")(request_context_middleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(NewsLensAPIException, api_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    api_prefix = settings.API_V1_STR
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(dashboard.router, prefix=api_prefix)
    app.include_router(articles.router, prefix=api_prefix)
    app.include_router(analysis.router, prefix=api_prefix)
    app.include_router(evidence.router, prefix=api_prefix)
    app.include_router(coverage.router, prefix=api_prefix)
    app.include_router(ingestion.router, prefix=api_prefix)
    app.include_router(integrations.router, prefix=api_prefix)
    app.include_router(methodology.router, prefix=api_prefix)

    _install_openapi_contract(app)

    return app


app = create_app()
