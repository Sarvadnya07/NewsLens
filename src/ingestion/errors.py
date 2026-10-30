"""Typed provider-error contracts for NewsLens India ingestion.

Kept deliberately free of any dependency on src.ingestion.models so the error
layer does not import the models layer (which would pull ProviderFetchResult and
NormalizedArticle into an error module). The service layer bridges the two;
this module only defines exception semantics.

Status strings exposed here must be kept in sync with src.ingestion.models
status constants by the service layer, not by cross-importing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class ProviderError(Exception):
    """Base class for ingestion provider failures.

    This is intentionally a separate base class from the one in
    src.ingestion.models.ProviderError. It is used only where the caller wants a
    clean "this query failed; try again / treat as unavailable" signal, without
    dragging in the full result-model machinery.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status: str = "provider_unavailable",
        status_code: Optional[int] = None,
        retryable: bool = False,
        original_exception: Optional[BaseException] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.message = message
        self.status = status
        self.status_code = status_code
        self.retryable = retryable
        self.original_exception = original_exception
        self.extra = extra or {}
        self.timestamp = datetime.now(tz=timezone.utc).isoformat()

    @property
    def sanitized_message(self) -> str:
        return self.message

    def __str__(self) -> str:
        base = f"[{self.provider}] {self.status}"
        if self.status_code is not None:
            base += f" (HTTP {self.status_code})"
        base += f": {self.message}"
        return base


class GdeltUnavailableError(ProviderError):
    """GDELT DOC API did not return a usable response for a query.

    Includes non-200 responses, JSON decode failures, and HTML error pages.
    Does NOT include genuine "200 + empty article list" outcomes — those raise
    EmptyResultError so the caller can distinguish 'no news' from 'unavailable'.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        original_exception: Optional[BaseException] = None,
        query: Optional[str] = None,
    ):
        super().__init__(
            provider="GDELT",
            message=message,
            status="provider_unavailable",
            status_code=status_code,
            retryable=(status_code is None or status_code in (429, 502, 503, 504)),
            original_exception=original_exception,
            extra={"query": query} if query else None,
        )


class FeedUnavailableError(ProviderError):
    """A specific RSS/Atom feed could not be retrieved or parsed within policy."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        feed_url: Optional[str] = None,
        status_code: Optional[int] = None,
        retryable: bool = False,
        original_exception: Optional[BaseException] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            status="provider_unavailable",
            status_code=status_code,
            retryable=retryable,
            original_exception=original_exception,
            extra={"feed_url": feed_url} if feed_url else None,
        )


class RateLimitedError(ProviderError):
    """A provider returned a rate-limit response (HTTP 429 for GDELT)."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        status_code: int = 429,
        retryable: bool = True,
        original_exception: Optional[BaseException] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            provider=provider,
            message=message,
            status="rate_limited",
            status_code=status_code,
            retryable=retryable,
            original_exception=original_exception,
            extra=extra,
        )


class EmptyResultError(Exception):
    """A provider returned a valid response with an empty article list.

    This is NOT a failure. Do not log it as "unavailable". The consumer can
    report "no news for this query" while still treating the source as
    reachable/healthy.
    """

    def __init__(self, provider: str, query: Optional[str] = None):
        super().__init__(f"{provider} returned no articles")
        self.provider = provider
        self.query = query
