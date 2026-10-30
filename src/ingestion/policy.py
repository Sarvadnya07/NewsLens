"""Shared ingestion policy constants for NewsLens India.

Kept in one place so that GDELT, RSS, and the service layer agree on
timeouts, retries, size limits, rate-limit behavior, and the distinction
between "no results" and "unavailable."
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# GDELT
# ---------------------------------------------------------------------------

GDELT_DOC_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"

# GDELT's public Doc API is a shared academic endpoint. Keep queries civil
# and do not hammer it: a minimum inter-request gap is enforced, and retries
# are bounded and only triggered by recoverable transport/timeout blips.
GDELT_MIN_INTERVAL_SECONDS = 5.0
GDELT_DEFAULT_REQUEST_TIMEOUT_SECONDS = 15
GDELT_DEFAULT_MAX_RETRIES = 1
GDELT_DEFAULT_RETRY_DELAY_SECONDS = 2.0

# ---------------------------------------------------------------------------
# RSS / Atom feeds
# ---------------------------------------------------------------------------

# Per-feed connect/read timeout.
RSS_FEED_TIMEOUT_SECONDS = 15

# Maximum size of a downloaded feed body we will accept.
RSS_MAX_FEED_BYTES = 5 * 1024 * 1024  # 5 MiB

# Maximum number of redirects we follow from a feed URL.
RSS_MAX_REDIRECTS = 4

# Schemes we ever accept for a feed or a redirect to it.
RSS_ALLOWED_SCHEMES = ("http", "https")

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

# How many recent articles the monitor dashboard considers "in view".
DEFAULT_MONITOR_WINDOW_DAYS = 7

# Default page size used by the UI's article carousels/lists.
DEFAULT_VIEW_LIMIT = 200

# Default GDELT max records in a single query.
DEFAULT_GDELT_MAX_RECORDS = 30
