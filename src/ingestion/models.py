"""Standardized result and error models for NewsLens India ingestion providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.models import NormalizedArticle

# Standardized source status taxonomy
STATUS_SUCCESS = "success"
STATUS_NO_RESULTS = "no_results"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_TIMEOUT = "timeout"
STATUS_PROVIDER_UNAVAILABLE = "provider_unavailable"
STATUS_INVALID_RESPONSE = "invalid_response"
STATUS_DISABLED = "disabled"
STATUS_NOT_ATTEMPTED = "not_attempted"

VALID_PROVIDER_STATUSES = frozenset(
    {
        STATUS_SUCCESS,
        STATUS_NO_RESULTS,
        STATUS_RATE_LIMITED,
        STATUS_TIMEOUT,
        STATUS_PROVIDER_UNAVAILABLE,
        STATUS_INVALID_RESPONSE,
        STATUS_DISABLED,
        STATUS_NOT_ATTEMPTED,
    }
)


class ProviderError(Exception):
    """Base exception for provider ingestion errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        status: str = STATUS_PROVIDER_UNAVAILABLE,
        status_code: Optional[int] = None,
        retryable: bool = False,
        original_exception: Optional[BaseException] = None,
        sanitized_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status = status if status in VALID_PROVIDER_STATUSES else STATUS_PROVIDER_UNAVAILABLE
        self.status_code = status_code
        self.retryable = retryable
        self.original_exception = original_exception
        self.sanitized_message = sanitized_message or self._sanitize(message)

    @staticmethod
    def _sanitize(msg: str) -> str:
        # Strip potential file paths, credentials, query parameters
        import re

        clean = re.sub(r"[C-Z]:\\[^\s]+", "[path]", str(msg))
        clean = re.sub(r"/(?:[a-zA-Z0-9_\-\.]+/)+[a-zA-Z0-9_\-\.]+", "[path]", clean)
        clean = re.sub(r"key=[^\s&]+", "key=[redacted]", clean)
        return clean.strip()[:200]


class ProviderRateLimitedError(ProviderError):
    """Raised when an ingestion provider responds with HTTP 429 / Rate Limited."""

    def __init__(
        self, message: str, provider: str, original_exception: Optional[BaseException] = None
    ):
        super().__init__(
            message=message,
            provider=provider,
            status=STATUS_RATE_LIMITED,
            status_code=429,
            retryable=False,
            original_exception=original_exception,
            sanitized_message=f"{provider} rate limit reached. Please wait before retrying.",
        )


class ProviderTimeoutError(ProviderError):
    """Raised when an ingestion request exceeds connect or read timeouts."""

    def __init__(
        self, message: str, provider: str, original_exception: Optional[BaseException] = None
    ):
        super().__init__(
            message=message,
            provider=provider,
            status=STATUS_TIMEOUT,
            status_code=None,
            retryable=True,
            original_exception=original_exception,
            sanitized_message=f"Connection to {provider} timed out.",
        )


class ProviderInvalidResponseError(ProviderError):
    """Raised when a provider returns invalid JSON, malformed XML, or oversized body."""

    def __init__(
        self, message: str, provider: str, original_exception: Optional[BaseException] = None
    ):
        super().__init__(
            message=message,
            provider=provider,
            status=STATUS_INVALID_RESPONSE,
            status_code=None,
            retryable=False,
            original_exception=original_exception,
            sanitized_message=f"Received invalid or malformed response from {provider}.",
        )


@dataclass
class ProviderFetchResult:
    """Canonical result object for an individual provider or feed fetch operation."""

    source_id: str
    source_name: str
    source_type: str  # 'gdelt' or 'rss'
    status: str  # One of VALID_PROVIDER_STATUSES
    articles: List[NormalizedArticle] = field(default_factory=list)
    items_count: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    last_attempt_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if self.articles and not self.items_count:
            self.items_count = len(self.articles)
        if self.status not in VALID_PROVIDER_STATUSES:
            self.status = STATUS_PROVIDER_UNAVAILABLE


@dataclass
class RefreshResult:
    """Canonical result object returned by NewsLensService ingestion refresh."""

    total_fetched: int
    new_stored: int
    duration_ms: float
    provider_results: Dict[str, ProviderFetchResult] = field(default_factory=dict)
    all_succeeded: bool = False
    all_failed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
