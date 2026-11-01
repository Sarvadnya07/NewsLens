"""Standalone CLI diagnostic tool for verifying NewsLens India external API integrations.

Usage:
    python scripts/verify_integrations.py
    python scripts/verify_integrations.py --provider currents
    python scripts/verify_integrations.py --provider guardian_open_platform
    python scripts/verify_integrations.py --provider google_fact_check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import redact_secret, settings  # noqa: E402
from src.ingestion.registry import PROVIDER_REGISTRY  # noqa: E402
from src.services.integration_service import IntegrationManager  # noqa: E402
from src.storage.database import DatabaseManager  # noqa: E402


def run_diagnostics(target_provider: str | None = None) -> int:
    print("=" * 70)
    print(" NEWSLENS INDIA - API INTEGRATION DIAGNOSTIC AUDIT")
    print("=" * 70)

    db = DatabaseManager()
    manager = IntegrationManager(db=db)

    providers_to_audit = [target_provider] if target_provider else list(PROVIDER_REGISTRY.keys())
    failures = 0

    for pid in providers_to_audit:
        desc = PROVIDER_REGISTRY.get(pid)
        if not desc:
            print(f"[!] Unknown provider identifier: '{pid}'")
            return 1

        print(f"\n[{desc.name}] (ID: {desc.id})")
        print(f"  Category:        {desc.category}")
        print(f"  Ingestion Type:  {desc.source_type}")
        print(f"  Endpoint:        {desc.endpoint_url}")

        if desc.requires_api_key:
            env_val = getattr(settings, desc.env_key_name or "", None)
            masked = redact_secret(env_val)
            print(f"  Credential Var:  {desc.env_key_name} -> {masked}")
            if not env_val:
                print("  Status:          AWAITING CREDENTIALS (Unconfigured)")
                continue

        # If configured or an open feed, perform minimal test
        print("  Running bounded reachability/auth test...")
        res = manager.test_provider_connection(desc.id)
        if res.get("success"):
            print(
                f"  Result:          PASSED ({res.get('status')}) - Latency: {res.get('latency_ms', 0):.1f}ms"
            )
            print(f"  Message:         {res.get('message')}")
        else:
            print(f"  Result:          FAILED/WARNING ({res.get('status')})")
            print(f"  Message:         {res.get('message')}")
            if desc.is_active and not desc.requires_api_key:
                failures += 1

    print("\n" + "=" * 70)
    print(" AUDIT COMPLETE")
    print("=" * 70)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewsLens India Integrations Diagnostic Tool")
    parser.add_argument("--provider", type=str, help="Audit a specific provider ID", default=None)
    args = parser.parse_args()
    sys.exit(run_diagnostics(target_provider=args.provider))
