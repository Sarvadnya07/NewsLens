"""Generate and verify the committed OpenAPI contract artifact.

Usage (from the repository root, inside the virtual environment):

    python scripts/export_openapi.py            # write docs/openapi.json
    python scripts/export_openapi.py --check    # fail if the artifact is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "docs" / "openapi.json"


def build_spec() -> dict:
    """Builds the OpenAPI document from the in-process FastAPI application."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from backend.main import create_app

    return create_app().openapi()


def serialize(spec: dict) -> str:
    """Deterministic serialisation: sorted keys, no timestamps, no secrets."""
    return json.dumps(spec, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_artifact(spec: dict, path: Path = ARTIFACT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize(spec), encoding="utf-8", newline="\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the committed artifact differs from the app.",
    )
    args = parser.parse_args(argv)

    spec = build_spec()
    rendered = serialize(spec)

    if args.check:
        if not ARTIFACT.exists():
            print(f"Missing contract artifact: {ARTIFACT}", file=sys.stderr)
            return 1
        if ARTIFACT.read_text(encoding="utf-8") != rendered:
            print(
                "OpenAPI artifact is stale. Regenerate with: python scripts/export_openapi.py",
                file=sys.stderr,
            )
            return 1
        print(f"OpenAPI artifact is up to date ({len(spec.get('paths', {}))} paths).")
        return 0

    write_artifact(spec)
    print(f"Wrote {ARTIFACT.relative_to(ROOT)} ({len(spec.get('paths', {}))} paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
