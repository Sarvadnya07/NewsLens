"""Verify that documented routes match the generated OpenAPI contract.

Documentation drift is a contract bug: this gate fails when a document
advertises a route or method the API does not implement, or when ``docs/API.md``
omits an implemented operation.

Usage (from the repository root):

    python scripts/check_doc_routes.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "docs" / "openapi.json"
DOCS: Dict[str, Path] = {
    "docs/API.md": ROOT / "docs" / "API.md",  # must document every operation
    "README.md": ROOT / "README.md",  # claims must be true; may be partial
}
COMPLETE_DOCS = {"docs/API.md"}

API_PREFIX = "/api/v1"
# `| `GET` | `/api/v1/articles` | ... |`
_ROW_RE = re.compile(r"\|\s*`(GET|POST|PUT|PATCH|DELETE)`\s*\|\s*`(/[^`\s]+)`")


def normalize(path: str) -> str:
    """Strips the version prefix and collapses path parameters for comparison."""
    cleaned = path.split("?", 1)[0].strip()
    if cleaned.startswith(API_PREFIX):
        cleaned = cleaned[len(API_PREFIX) :]
    cleaned = re.sub(r"\{[^}]*\}", "{}", cleaned)
    return cleaned.rstrip("/") or "/"


def spec_operations(spec: dict) -> Set[Tuple[str, str]]:
    operations: Set[Tuple[str, str]] = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            operations.add((method.upper(), normalize(path)))
    return operations


def documented_operations(text: str) -> Set[Tuple[str, str]]:
    return {(method, normalize(path)) for method, path in _ROW_RE.findall(text)}


def main() -> int:
    if not SPEC_PATH.exists():
        print(f"Missing {SPEC_PATH}; run python scripts/export_openapi.py first.", file=sys.stderr)
        return 1

    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    implemented = spec_operations(spec)
    problems: List[str] = []
    summary: Dict[str, int] = {}

    for label, path in DOCS.items():
        if not path.exists():
            problems.append(f"{label} is missing")
            continue

        documented = documented_operations(path.read_text(encoding="utf-8"))
        summary[label] = len(documented)

        for method, route in sorted(documented - implemented):
            problems.append(
                f"{label} documents {method} {API_PREFIX}{route}, which is not implemented"
            )

        if label in COMPLETE_DOCS:
            for method, route in sorted(implemented - documented):
                problems.append(f"{label} does not document {method} {API_PREFIX}{route}")

    if problems:
        print("Documentation/contract drift detected:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    detail = ", ".join(f"{label}: {count}" for label, count in sorted(summary.items()))
    print(
        f"Documented routes match the OpenAPI contract ({detail}; {len(implemented)} operations)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
