"""FastAPI routing module for the Central API Integrations Management System."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_integration_manager, verify_admin_access
from backend.schemas.common import APIResponse
from backend.schemas.integrations import (
    ConnectionTestResult,
    IntegrationRefreshRequest,
    IntegrationRefreshResult,
    IntegrationsOverview,
    ProviderStatusItem,
)
from src.services.integration_service import IntegrationManager

router = APIRouter(prefix="/integrations", tags=["Integrations"])


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
    status = manager.get_provider_status(provider_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return APIResponse(data=ProviderStatusItem(**status))


@router.post("/{provider_id}/test", response_model=APIResponse[ConnectionTestResult])
def test_provider(
    provider_id: str,
    manager: IntegrationManager = Depends(get_integration_manager),
    _authorized: bool = Depends(verify_admin_access),
):
    """Executes a safe, minimal connection test for the provider.

    Requires administrative authorization in production mode.
    """
    result = manager.test_provider_connection(provider_id)
    return APIResponse(data=ConnectionTestResult(**result))


@router.post("/{provider_id}/refresh", response_model=APIResponse[IntegrationRefreshResult])
def refresh_provider_endpoint(
    provider_id: str,
    payload: IntegrationRefreshRequest = IntegrationRefreshRequest(),
    manager: IntegrationManager = Depends(get_integration_manager),
    _authorized: bool = Depends(verify_admin_access),
):
    """Triggers an on-demand ingestion cycle for the specific provider.

    Requires administrative authorization in production mode.
    """
    result = manager.refresh_provider(
        provider_id=provider_id,
        profile=payload.profile,
        query=payload.query,
        max_pages=payload.max_pages or 1,
    )
    return APIResponse(data=IntegrationRefreshResult(**result))


@router.get("/{provider_id}/quota", response_model=APIResponse[Dict[str, Any]])
def get_provider_quota_endpoint(
    provider_id: str,
    manager: IntegrationManager = Depends(get_integration_manager),
):
    """Returns detailed quota ledger metrics for the specified provider."""
    status = manager.get_provider_status(provider_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    quota = status.get("quota") or {
        "provider_id": provider_id,
        "daily_limit": None,
        "daily_consumed": 0,
        "daily_remaining": None,
        "rolling_15m_consumed": 0,
    }
    return APIResponse(data=quota)
