"""Pydantic schemas for the centralized API Integrations management system."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderStatusItem(BaseModel):
    id: str
    name: str
    category: str
    source_type: str
    domain: str
    is_active: bool
    requires_api_key: bool
    env_key_name: Optional[str] = None
    is_configured: bool
    is_enabled: bool
    status_label: str  # 'operational', 'configured_not_tested', 'not_configured', 'disabled', 'rate_limited', 'provider_error', 'retired', 'backlog'
    last_refresh_at: Optional[str] = None
    last_attempt_at: Optional[str] = None
    last_attempt_status: Optional[str] = None
    last_http_status: Optional[int] = None
    last_latency_ms: Optional[float] = None
    items_count: int = 0
    new_items_inserted: int = 0
    error_message: Optional[str] = None
    quota: Optional[Dict[str, Any]] = None
    supported_profiles: List[str] = Field(default_factory=list)
    documentation_url: Optional[str] = None
    terms_url: Optional[str] = None


class IntegrationsOverview(BaseModel):
    total_registered: int
    configured_count: int
    operational_count: int
    disabled_count: int
    awaiting_credentials_count: int
    providers: List[ProviderStatusItem]


class ConnectionTestResult(BaseModel):
    provider_id: str
    success: bool
    status: str
    message: str
    http_status: Optional[int] = None
    latency_ms: Optional[float] = None


class IntegrationRefreshRequest(BaseModel):
    profile: Optional[str] = None
    query: Optional[str] = None
    max_pages: Optional[int] = 1


class IntegrationRefreshResult(BaseModel):
    provider_id: str
    profile: Optional[str] = None
    success: bool
    status: str
    items_fetched: int
    new_stored: int
    duration_ms: float
    error_message: Optional[str] = None
