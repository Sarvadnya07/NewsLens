"""NewsData.io live upstream connectivity and diagnostic verification script.

Safely tests authentication, query profiles, and quota metrics without ever
logging or printing the secret key.
"""

from __future__ import annotations

import os
import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load local environment if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src.ingestion.newsdata import (
    PROFILE_GLOBAL_LATEST,
    PROFILE_INDIA_GLOBAL_COVERAGE,
    PROFILE_INDIA_PUBLISHERS,
    NewsDataClient,
)
from src.ingestion.registry import CANONICAL_NEWSDATA_ID, CANONICAL_NEWSDATA_NAME
from src.storage.database import DatabaseManager


def main() -> int:
    print("=" * 60)
    print(
        f"NewsLens India — {CANONICAL_NEWSDATA_NAME} ({CANONICAL_NEWSDATA_ID}) Connectivity Audit"
    )
    print("=" * 60)

    api_key = os.environ.get("NEWSDATA_API_KEY", "").strip()
    enabled = os.environ.get("NEWSDATA_ENABLED", "true").lower() in ("true", "1", "yes")

    print(f"Provider Enabled : {enabled}")
    if not api_key:
        print("API Key Status   : NOT CONFIGURED (NEWSDATA_API_KEY is empty or missing)")
        print("\n[BLOCKED] Live upstream verification cannot proceed without an API key.")
        print("To configure, add NEWSDATA_API_KEY=<key> to your .env file or environment.")
        return 1

    # Safe display with redaction: only show length and first/last 2 chars
    masked_key = f"{api_key[:2]}***{api_key[-2:]}" if len(api_key) > 4 else "***"
    print(f"API Key Status   : CONFIGURED (Key: {masked_key}, length: {len(api_key)})")

    client = NewsDataClient(api_key=api_key)

    # 1. Test basic authentication ping
    print("\n1. Testing Upstream Authentication Ping...")
    diag = client.test_upstream_connectivity()
    status = diag.get("status")
    print(f"   Outcome       : {status}")
    print(f"   Authenticated : {diag.get('authenticated')}")
    if status != "SUCCESS":
        print(f"   Details       : {diag}")
        print("\n[FAILED] Upstream connectivity check failed.")
        return 1

    print(f"   Latency       : {diag.get('latency_ms')} ms")
    print(f"   Total Results : {diag.get('total_results')}")

    # 2. Test India Publishers profile
    print("\n2. Testing 'india_publishers' Profile...")
    res_in = client.fetch_profile(PROFILE_INDIA_PUBLISHERS, max_pages=1)
    print(f"   Status        : {res_in.status}")
    print(f"   Items Fetched : {res_in.items_count}")
    if res_in.articles:
        sample = res_in.articles[0]
        print(f"   Sample Title  : {sample.title[:65]}...")
        print(f"   Publisher     : {sample.publisher} (Country: {sample.country})")

    # 3. Test Global Latest profile
    print("\n3. Testing 'global_latest' Profile...")
    res_gl = client.fetch_profile(PROFILE_GLOBAL_LATEST, max_pages=1)
    print(f"   Status        : {res_gl.status}")
    print(f"   Items Fetched : {res_gl.items_count}")
    if res_gl.articles:
        sample = res_gl.articles[0]
        print(f"   Sample Title  : {sample.title[:65]}...")
        print(f"   Publisher     : {sample.publisher} (Country: {sample.country})")

    # 4. Test International Reporting on India profile
    print("\n4. Testing 'india_global_coverage' Profile...")
    res_ig = client.fetch_profile(PROFILE_INDIA_GLOBAL_COVERAGE, max_pages=1)
    print(f"   Status        : {res_ig.status}")
    print(f"   Items Fetched : {res_ig.items_count}")
    if res_ig.articles:
        sample = res_ig.articles[0]
        print(f"   Sample Title  : {sample.title[:65]}...")
        print(f"   Publisher     : {sample.publisher} (Country: {sample.country})")

    # 5. Check persistent quota
    db = DatabaseManager()
    quota = db.get_provider_quota_telemetry(CANONICAL_NEWSDATA_ID)
    print("\n5. Quota Governance Snapshot:")
    print(f"   Daily Used    : {quota['daily_requests_used']} / {quota['daily_requests_budget']}")
    print(f"   Rolling 15m   : {quota['rolling_15m_used']} / {quota['rolling_15m_budget']}")
    print(f"   Last Request  : {quota['last_request_at']}")

    print("\n[SUCCESS] NewsData.io live upstream connectivity verified successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
