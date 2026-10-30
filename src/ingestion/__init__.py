"""NewsLens India ingestion package.

Public wrappers are re-exported here so existing imports that reach into
`src.ingestion` continue to resolve without failing on missing submodules.
"""

from __future__ import annotations

try:
    from src.ingestion.errors import (
        EmptyResultError,
        FeedUnavailableError,
        GdeltUnavailableError,
        ProviderError,
        RateLimitedError,
    )
except ImportError:  # pragma: no cover - defensive fallback if errors.py is absent
    EmptyResultError = None  # type: ignore[assignment]
    FeedUnavailableError = None  # type: ignore[assignment]
    GdeltUnavailableError = None  # type: ignore[assignment]
    ProviderError = None  # type: ignore[assignment]
    RateLimitedError = None  # type: ignore[assignment]

try:
    from src.ingestion.gdelt import GdeltClient
except ImportError:  # pragma: no cover
    GdeltClient = None  # type: ignore[assignment]

try:
    from src.ingestion.rss import DEFAULT_INDIAN_FEEDS, RssIngestionService
except ImportError:  # pragma: no cover
    DEFAULT_INDIAN_FEEDS = None  # type: ignore[assignment]
    RssIngestionService = None  # type: ignore[assignment]

try:
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
except ImportError:  # pragma: no cover
    DEFAULT_GDELT_MAX_RECORDS = None  # type: ignore[assignment]
    DEFAULT_MONITOR_WINDOW_DAYS = None  # type: ignore[assignment]
    DEFAULT_VIEW_LIMIT = None  # type: ignore[assignment]
    GDELT_DOC_ENDPOINT = None  # type: ignore[assignment]
    GDELT_DEFAULT_MAX_RETRIES = None  # type: ignore[assignment]
    GDELT_DEFAULT_REQUEST_TIMEOUT_SECONDS = None  # type: ignore[assignment]
    GDELT_DEFAULT_RETRY_DELAY_SECONDS = None  # type: ignore[assignment]
    GDELT_MIN_INTERVAL_SECONDS = None  # type: ignore[assignment]
    RSS_ALLOWED_SCHEMES = None  # type: ignore[assignment]
    RSS_FEED_TIMEOUT_SECONDS = None  # type: ignore[assignment]
    RSS_MAX_FEED_BYTES = None  # type: ignore[assignment]
    RSS_MAX_REDIRECTS = None  # type: ignore[assignment]

try:
    from src.ingestion.master_news_pipeline import MasterNewsPipeline
except ImportError:  # pragma: no cover
    MasterNewsPipeline = None  # type: ignore[assignment]

__all__ = [
    "EmptyResultError",
    "FeedUnavailableError",
    "GdeltUnavailableError",
    "GdeltClient",
    "MasterNewsPipeline",
    "ProviderError",
    "RateLimitedError",
    "RssIngestionService",
    "DEFAULT_INDIAN_FEEDS",
    "DEFAULT_GDELT_MAX_RECORDS",
    "DEFAULT_MONITOR_WINDOW_DAYS",
    "DEFAULT_VIEW_LIMIT",
    "GDELT_DOC_ENDPOINT",
    "GDELT_DEFAULT_MAX_RETRIES",
    "GDELT_DEFAULT_REQUEST_TIMEOUT_SECONDS",
    "GDELT_DEFAULT_RETRY_DELAY_SECONDS",
    "GDELT_MIN_INTERVAL_SECONDS",
    "RSS_ALLOWED_SCHEMES",
    "RSS_FEED_TIMEOUT_SECONDS",
    "RSS_MAX_FEED_BYTES",
    "RSS_MAX_REDIRECTS",
]
