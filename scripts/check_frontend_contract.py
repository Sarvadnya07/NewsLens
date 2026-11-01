"""Verify the frontend transport types against the OpenAPI contract.

Usage (from the repository root):

    python scripts/check_frontend_contract.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "docs" / "openapi.json"
TS_PATH = ROOT / "frontend" / "src" / "types" / "api.ts"

# OpenAPI component schema -> TypeScript interface name.
SCHEMA_TO_INTERFACE: Dict[str, str] = {
    "APIResponse_dict_": "APIResponse",
    "ProblemDetails": "ProblemDetails",
    "ProblemFieldError": "ProblemFieldError",
    "ArticleResponse": "Article",
    "ArticleDetailResponse": "Article",
    "PaginationMeta": "PaginationMeta",
    "PaginatedResponse_ArticleResponse_": "PaginatedResponse",
    "DashboardSummary": "DashboardSummary",
    "SourceStatusItem": "SourceStatusItem",
    "AnalysisResponse": "AnalysisResponse",
    "MLScreeningResult": "MLScreeningResult",
    "InfluentialToken": "InfluentialToken",
    "EvidenceSearchResponse": "EvidenceSearchResponse",
    "FactCheckItem": "FactCheckItem",
    "CoverageGraphResponse": "CoverageGraphResponse",
    "GraphNode": "GraphNode",
    "GraphEdge": "GraphEdge",
    "MethodologyResponse": "MethodologyResponse",
    "PipelineStage": "PipelineStage",
    "MetricEvaluation": "MetricEvaluation",
    "SystemLimitation": "SystemLimitation",
    "IngestionRefreshResponse": "IngestionRefreshResponse",
}

# Schemas that only exist while an optional feature is present in the build.
OPTIONAL_SCHEMAS = {
    "ProviderStatusItem",
    "ProviderQuotaTelemetry",
    "IntegrationsOverview",
    "ConnectionTestResult",
    "IntegrationRefreshResult",
}

_INTERFACE_RE = re.compile(r"export interface (\w+)(?:<[^>]*>)?\s*\{(.*?)\n\}", re.DOTALL)
_FIELD_RE = re.compile(r"^\s*(\w+)\??\s*:", re.MULTILINE)


def parse_typescript_interfaces(text: str) -> Dict[str, List[str]]:
    interfaces: Dict[str, List[str]] = {}
    for match in _INTERFACE_RE.finditer(text):
        interfaces[match.group(1)] = _FIELD_RE.findall(match.group(2))
    return interfaces


def main() -> int:
    if not SPEC_PATH.exists():
        print(f"Missing {SPEC_PATH}; run python scripts/export_openapi.py first.", file=sys.stderr)
        return 1
    if not TS_PATH.exists():
        print(f"Missing {TS_PATH}.", file=sys.stderr)
        return 1

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    schemas = spec.get("components", {}).get("schemas", {})
    interfaces = parse_typescript_interfaces(TS_PATH.read_text(encoding="utf-8"))

    problems: List[str] = []
    checked = 0

    for schema_name, interface_name in sorted(SCHEMA_TO_INTERFACE.items()):
        schema = schemas.get(schema_name)
        if schema is None:
            problems.append(f"OpenAPI schema '{schema_name}' is missing from the spec")
            continue
        fields = interfaces.get(interface_name)
        if fields is None:
            problems.append(f"TypeScript interface '{interface_name}' is missing")
            continue
        checked += 1
        missing = sorted(set(schema.get("properties", {})) - set(fields))
        if missing:
            problems.append(
                f"{interface_name} (from {schema_name}) is missing: {', '.join(missing)}"
            )

    for schema_name in sorted(OPTIONAL_SCHEMAS & set(schemas)):
        interface_name = schema_name
        fields = interfaces.get(interface_name)
        if fields is None:
            problems.append(f"TypeScript interface '{interface_name}' is missing")
            continue
        checked += 1
        missing = sorted(set(schemas[schema_name].get("properties", {})) - set(fields))
        if missing:
            problems.append(
                f"{interface_name} (from {schema_name}) is missing: {', '.join(missing)}"
            )

    if problems:
        print("Frontend contract drift detected:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"Frontend transport types match the OpenAPI contract ({checked} schemas checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
