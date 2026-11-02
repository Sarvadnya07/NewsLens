"""FastAPI routing module for the Central API Integrations Management System.

Every provider diagnostic answers with the same normalized shape
(``ConnectionTestResult``) so consumers never have to interpret
provider-specific strings. Provider failures map onto stable application codes
through ``NewsLensAPIException`` rather than ad-hoc payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterator, List

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies import get_integration_manager
from backend.api.errors import NewsLensAPIException
from backend.schemas.common import APIResponse
from backend.schemas.integrations import (
    ConnectionState,
    ConnectionTestResult,
    IntegrationRefreshRequest,
    IntegrationRefreshResult,
    IntegrationsOverview,
    ProviderQuotaTelemetry,
    ProviderStatusItem,
)
from src.services.integration_service import IntegrationManager

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# Provider adapter status strings -> stable public connection states.
# Anything unrecognised becomes ``error`` (or ``connected`` when the adapter
# explicitly reported success), so a provider can never invent a new state.
_CONNECTION_STATES = {
    "connected": ConnectionState.CONNECTED,
    "success": ConnectionState.CONNECTED,
    "ok": ConnectionState.CONNECTED,
    "operational": ConnectionState.CONNECTED,
    "no_results": ConnectionState.CONNECTED,
    "not_configured": ConnectionState.NOT_CONFIGURED,
    "blocked": ConnectionState.NOT_CONFIGURED,
    "missing_key": ConnectionState.NOT_CONFIGURED,
    "unsupported": ConnectionState.NOT_IMPLEMENTED,
    "not_implemented": ConnectionState.NOT_IMPLEMENTED,
    "unauthorized": ConnectionState.AUTH_FAILED,
    "auth_failed": ConnectionState.AUTH_FAILED,
    "invalid_key": ConnectionState.AUTH_FAILED,
    "rate_limited": ConnectionState.RATE_LIMITED,
    "quota_exceeded": ConnectionState.RATE_LIMITED,
    "timeout": ConnectionState.TIMEOUT,
    "unreachable": ConnectionState.UNAVAILABLE,
    "unavailable": ConnectionState.UNAVAILABLE,
    "provider_unavailable": ConnectionState.UNAVAILABLE,
    "invalid_response": ConnectionState.INVALID_RESPONSE,
    "failed": ConnectionState.ERROR,
    "error": ConnectionState.ERROR,
}


def _normalize_state(raw_status: object, success: bool) -> ConnectionState:
    """Maps an adapter status onto the canonical connection-state enum."""
    mapped = _CONNECTION_STATES.get(str(raw_status or "").strip().lower())
    if mapped is not None:
        return mapped
    return ConnectionState.CONNECTED if success else ConnectionState.ERROR


def _authorize(request: Request, scope: str) -> bool:
    """Applies the single centralized admin policy, then the request budget.

    Delegated lazily to ``backend.main`` because that module includes this
    router. The policy is identical for every privileged endpoint: production
    always requires ``X-Admin-Key``, development bypasses only loopback clients.
    """
    from backend.main import enforce_rate_limit, verify_admin_access

    verify_admin_access(request)
    enforce_rate_limit(request, scope=scope)
    return True


def require_test_admin(request: Request) -> bool:
    """Authorization + rate-limit gate for provider connection tests."""
    return _authorize(request, "integrations:test")


def require_refresh_admin(request: Request) -> bool:
    """Authorization + rate-limit gate for provider refreshes."""
    return _authorize(request, "integrations:refresh")


def _status_or_404(manager: IntegrationManager, provider_id: str) -> dict:
    """Returns provider status or raises the stable ``PROVIDER_NOT_FOUND`` problem."""
    status = manager.get_provider_status(provider_id)
    if not status:
        raise NewsLensAPIException(
            code="PROVIDER_NOT_FOUND",
            message=f"Provider '{provider_id}' is not registered.",
            status_code=404,
        )
    return status


def _provider_refresh_slot(request: Request) -> Iterator[None]:
    """Single-flight guard so one provider cannot be refreshed concurrently."""
    from backend.main import refresh_coordinator

    provider_id = str(request.path_params.get("provider_id", ""))
    key = f"provider:{provider_id}"
    if not refresh_coordinator.try_start(key):
        raise NewsLensAPIException(
            code="CONFLICT",
            message=f"A refresh for '{provider_id}' is already running.",
            status_code=409,
        )
    try:
        yield
    finally:
        refresh_coordinator.finish(key)


@router.get("", response_model=APIResponse[IntegrationsOverview])
def get_integrations_overview(
    manager: IntegrationManager = Depends(get_integration_manager),
):
    """Returns overview metrics and individual status for all registered providers."""
    providers_raw = manager.get_all_provider_statuses()
    items = [ProviderStatusItem(**p) for p in providers_raw]

    total = len(items)
    configured = sum(1 for p in items if p.is_configured and p.is_active)
    operational = sum(1 for p in items if p.status_label == "operational")
    disabled = sum(1 for p in items if not p.is_enabled and p.is_active)
    awaiting = sum(1 for p in items if p.requires_api_key and not p.is_configured and p.is_active)

    return APIResponse(
        data=IntegrationsOverview(
            total_registered=total,
            configured_count=configured,
            operational_count=operational,
            disabled_count=disabled,
            awaiting_credentials_count=awaiting,
            providers=items,
        )
    )


@router.get("/status", response_model=APIResponse[List[ProviderStatusItem]])
def list_provider_statuses(
    manager: IntegrationManager = Depends(get_integration_manager),
):
    """Returns status list for all providers."""
    providers_raw = manager.get_all_provider_statuses()
    return APIResponse(data=[ProviderStatusItem(**p) for p in providers_raw])


@router.get("/{provider_id}", response_model=APIResponse[ProviderStatusItem])
def get_single_provider(
    provider_id: str,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    """Returns detailed status and quota telemetry for a specific provider."""
    return APIResponse(data=ProviderStatusItem(**_status_or_404(manager, provider_id)))


@router.get("/{provider_id}/quota", response_model=APIResponse[ProviderQuotaTelemetry])
def get_provider_quota_endpoint(
    provider_id: str,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    """Returns request-budget telemetry for the specified provider.

    NewsLens budgets are internal governance counters, not provider-reported
    subscription quotas. Providers without a managed budget answer with
    ``quota_supported: false`` and null measurements rather than invented zeros.
    """
    status = _status_or_404(manager, provider_id)
    quota = status.get("quota")
    if not quota:
        return APIResponse(data=ProviderQuotaTelemetry.model_validate({"provider_id": provider_id}))
    if isinstance(quota, ProviderQuotaTelemetry):
        return APIResponse(data=quota)
    if isinstance(quota, dict):
        # Validate instead of splatting: a malformed telemetry blob must surface
        # as a schema error, not as a 500 from an unchecked **kwargs expansion.
        return APIResponse(
            data=ProviderQuotaTelemetry.model_validate({"provider_id": provider_id, **quota})
        )
    return APIResponse(data=ProviderQuotaTelemetry.model_validate({"provider_id": provider_id}))


@router.post("/{provider_id}/test", response_model=APIResponse[ConnectionTestResult])
def test_provider(
    provider_id: str,
    request: Request,
    manager: IntegrationManager = Depends(get_integration_manager),
    _authorized: bool = Depends(require_test_admin),
):
    """Executes a safe, bounded connection test for the provider.

    No articles are ingested. Requires administrative authorization and consumes
    one unit of the provider-diagnostics rate-limit budget.
    """
    status = _status_or_404(manager, provider_id)
    payload = manager.test_provider_connection(provider_id)
    state = _normalize_state(payload.get("status"), bool(payload.get("success")))
    connected = state is ConnectionState.CONNECTED
    message = str(payload.get("message") or "")

    return APIResponse(
        data=ConnectionTestResult(
            provider_id=provider_id,
            status=state,
            connected=connected,
            configured=bool(status.get("is_configured")),
            implemented=state is not ConnectionState.NOT_IMPLEMENTED,
            success=connected,
            message=message,
            checked_at=datetime.now(timezone.utc).isoformat(),
            http_status=payload.get("http_status"),
            latency_ms=payload.get("latency_ms"),
            error=None if connected else (message or None),
            request_id=getattr(request.state, "request_id", None),
        )
    )


@router.post("/{provider_id}/refresh", response_model=APIResponse[IntegrationRefreshResult])
def refresh_provider_endpoint(
    provider_id: str,
    payload: IntegrationRefreshRequest = IntegrationRefreshRequest.model_validate({}),
    manager: IntegrationManager = Depends(get_integration_manager),
    _authorized: bool = Depends(require_refresh_admin),
    _slot: None = Depends(_provider_refresh_slot),
):
    """Triggers an on-demand ingestion cycle for the specific provider.

    Requires administrative authorization and consumes one unit of the
    provider-diagnostics rate-limit budget.
    """
    _status_or_404(manager, provider_id)
    result = manager.refresh_provider(
        provider_id=provider_id,
        profile=payload.profile,
        query=payload.query,
        max_pages=payload.max_pages or 1,
    )
    return APIResponse(data=IntegrationRefreshResult(**result))
