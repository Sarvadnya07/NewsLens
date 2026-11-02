"""NewsLens India ingestion package.

Explicit re-exports only. A missing submodule must fail loudly at import time
rather than silently degrade to ``None`` - which is what the previous
``try/except ImportError`` shim did, hiding breakage behind 21 suppressions.
"""

from __future__ import annotations

from src.ingestion.errors import (
    EmptyResultError,
    FeedUnavailableError,
    GdeltUnavailableError,
    ProviderError,
    RateLimitedError,
)
from src.ingestion.gdelt import GdeltClient
from src.ingestion.policy import (
    DEFAULT_GDELT_MAX_RECORDS,
    DEFAULT_MONITOR_WINDOW_DAYS,
    DEFAULT_VIEW_LIMIT,
    GDELT_DEFAULT_MAX_RETRIES,
    GDELT_DEFAULT_REQUEST_TIMEOUT_SECONDS,
    GDELT_DEFAULT_RETRY_DELAY_SECONDS,
    GDELT_DOC_ENDPOINT,
    GDELT_MIN_INTERVAL_SECONDS,
    RSS_ALLOWED_SCHEMES,
    RSS_FEED_TIMEOUT_SECONDS,
    RSS_MAX_FEED_BYTES,
    RSS_MAX_REDIRECTS,
)
from src.ingestion.rss import DEFAULT_INDIAN_FEEDS, RssIngestionService

__all__ = [
    "DEFAULT_GDELT_MAX_RECORDS",
    "DEFAULT_INDIAN_FEEDS",
    "DEFAULT_MONITOR_WINDOW_DAYS",
    "DEFAULT_VIEW_LIMIT",
    "EmptyResultError",
    "FeedUnavailableError",
    "GDELT_DEFAULT_MAX_RETRIES",
    "GDELT_DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "GDELT_DEFAULT_RETRY_DELAY_SECONDS",
    "GDELT_DOC_ENDPOINT",
    "GDELT_MIN_INTERVAL_SECONDS",
    "GdeltClient",
    "GdeltUnavailableError",
    "ProviderError",
    "RSS_ALLOWED_SCHEMES",
    "RSS_FEED_TIMEOUT_SECONDS",
    "RSS_MAX_FEED_BYTES",
    "RSS_MAX_REDIRECTS",
    "RateLimitedError",
    "RssIngestionService",
]
