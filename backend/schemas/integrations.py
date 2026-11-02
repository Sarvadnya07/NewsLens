"""Pydantic schemas for the centralized API Integrations management system.

These are public API DTOs. Provider maturity is expressed with explicit enums so
"configured" is never confused with "implemented", "tested", or "operational".
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class IntegrationStatus(str, Enum):
    """Canonical provider state exposed to consumers.

    * ``operational`` - a successful attempt was recorded inside the staleness window.
    * ``degraded`` - the last recorded attempt succeeded but is older than the
      staleness window, so it no longer proves current health.
    * ``configured_not_tested`` - credentials or configuration exist, but no
      successful attempt has been recorded.
    * ``not_configured`` - the provider requires credentials that are absent.
    * ``disabled`` - explicitly disabled in configuration.
    * ``rate_limited`` - the last attempt was rejected by an upstream quota.
    * ``provider_error`` - the last attempt failed (timeout, 5xx, bad payload).
    * ``backlog`` - registered for planning; no adapter is active.
    * ``retired`` - withdrawn; excluded from normal ingestion.
    """

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    CONFIGURED_NOT_TESTED = "configured_not_tested"
    NOT_CONFIGURED = "not_configured"
    DISABLED = "disabled"
    RATE_LIMITED = "rate_limited"
    PROVIDER_ERROR = "provider_error"
    BACKLOG = "backlog"
    RETIRED = "retired"


class ConnectionState(str, Enum):
    """Outcome of a single bounded connectivity test.

    ``connected`` is only returned when the provider actually answered; a
    configured API key alone is never reported as connectivity.
    """

    CONNECTED = "connected"
    NOT_CONFIGURED = "not_configured"
    NOT_IMPLEMENTED = "not_implemented"
    AUTH_FAILED = "auth_failed"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"
    ERROR = "error"


class ProviderQuotaTelemetry(BaseModel):
    """NewsLens request-budget telemetry for one provider.

    This is internal governance (how much of our own configured request budget
    has been spent), not a provider-reported subscription quota. When a provider
    has no managed budget, every measurement is null and ``quota_supported`` is
    false; values are never fabricated.
    """

    provider_id: str
    quota_supported: bool = Field(
        False, description="False when NewsLens keeps no request budget for this provider"
    )
    limit: Optional[int] = Field(None, description="Daily request budget, when managed")
    used: Optional[int] = Field(None, description="Requests consumed in the current day window")
    remaining: Optional[int] = Field(None, description="Remaining daily requests, when managed")
    window: str = Field("daily", description="Budget window the limit applies to")
    reset_at: Optional[str] = Field(None, description="Window reset timestamp, when known")
    unit: str = Field("requests", description="Unit counted by limit/used")
    source: str = Field(
        "newslens_request_budget",
        description="Where the numbers come from (internal governance, not the provider)",
    )
    rolling_15m_used: Optional[int] = Field(None, description="Requests in the 15-minute window")
    rolling_15m_limit: Optional[int] = Field(None, description="15-minute burst budget")
    is_exhausted: Optional[bool] = Field(None, description="True when either budget is spent")
    last_request_at: Optional[str] = Field(None, description="Timestamp of the last request")
    last_outcome: Optional[str] = Field(None, description="Outcome of the last request")
    last_updated_at: Optional[str] = Field(None, description="When these counters were read")


class ProviderStatusItem(BaseModel):
    """Public status DTO for one registered provider."""

    id: str
    name: str
    category: str
    source_type: str
    domain: str
    is_active: bool
    requires_api_key: bool
    env_key_name: Optional[str] = None
    is_configured: bool = Field(..., description="Required credentials are present")
    is_enabled: bool = Field(..., description="Provider is enabled in configuration")
    status_label: IntegrationStatus = Field(..., description="Truthful provider maturity state")
    last_refresh_at: Optional[str] = None
    last_attempt_at: Optional[str] = None
    last_attempt_status: Optional[str] = None
    last_http_status: Optional[int] = None
    last_latency_ms: Optional[float] = None
    items_count: int = 0
    new_items_inserted: int = 0
    error_message: Optional[str] = None
    quota: Optional[ProviderQuotaTelemetry] = None
    supported_profiles: List[str] = Field(default_factory=list)
    documentation_url: Optional[str] = None
    terms_url: Optional[str] = None


class IntegrationsOverview(BaseModel):
    """Registry-wide aggregates for the Integrations page."""

    total_registered: int
    configured_count: int
    operational_count: int
    disabled_count: int
    awaiting_credentials_count: int
    providers: List[ProviderStatusItem]


class ConnectionTestResult(BaseModel):
    """Normalized result of ``POST /integrations/{provider_id}/test``.

    Every provider answers with this exact structure. Optional measurements stay
    null when no request could be made; they are never synthesized.
    """

    provider_id: str
    status: ConnectionState = Field(..., description="Canonical outcome of the test")
    connected: bool = Field(..., description="True only when the upstream answered")
    configured: bool = Field(..., description="Required credentials are present")
    implemented: bool = Field(..., description="An adapter exists for this provider")
    success: bool = Field(..., description="Alias of ``connected`` for legacy consumers")
    message: str = Field("", description="Safe, human readable summary")
    checked_at: str = Field(..., description="ISO-8601 UTC timestamp of this test")
    http_status: Optional[int] = Field(None, description="Upstream status, when a call was made")
    latency_ms: Optional[float] = Field(None, description="Measured round trip, when available")
    error: Optional[str] = Field(None, description="Failure summary; null when connected")
    request_id: Optional[str] = Field(None, description="Correlation id for this request")


class IntegrationRefreshRequest(BaseModel):
    """Optional scoping for an on-demand provider refresh."""

    profile: Optional[str] = None
    query: Optional[str] = None
    max_pages: Optional[int] = Field(1, ge=1, le=10)


class IntegrationRefreshResult(BaseModel):
    """Result of ``POST /integrations/{provider_id}/refresh``.

    ``status`` uses the ingestion provider-status vocabulary
    (``success``, ``no_results``, ``disabled``, ``rate_limited``,
    ``provider_unavailable``, ``timeout``, ``invalid_response``,
    ``not_implemented``).
    """

    provider_id: str
    profile: Optional[str] = None
    success: bool
    status: str
    items_fetched: int = 0
    new_stored: int = 0
    duration_ms: float = 0.0
    error_message: Optional[str] = None
