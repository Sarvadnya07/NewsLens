"""Repository-level quality gates.

These guard the two failure modes an audit found in this codebase:

1. A module can sit in ``tests/`` and never be collected, because pytest only
   collects ``test_*.py`` / ``*_test.py``. A stale, failing module was invisible
   to CI for exactly this reason.
2. The domain engine can import the API layer, which inverts the dependency
   direction and makes ``src`` unusable without the web package.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
SRC = ROOT / "src"

COLLECTIBLE = re.compile(r"^(test_.*|.*_test)\.py$|^(conftest|__init__)\.py$")
API_IMPORT = re.compile(r"^\s*(?:from|import)\s+backend(?:[.\s]|$)", re.MULTILINE)


def test_every_module_in_tests_directory_is_collected():
    """A test file pytest never selects is dead weight that can rot silently."""
    uncollected = sorted(
        path.name for path in TESTS.glob("*.py") if not COLLECTIBLE.match(path.name)
    )
    assert uncollected == [], (
        "These files live in tests/ but pytest will never collect them "
        f"(rename to test_*.py or delete): {uncollected}"
    )


def test_domain_engine_does_not_import_the_api_layer():
    """src/ is the engine; backend/ is the transport shell. Depend inward only."""
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if API_IMPORT.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], (
        f"Domain modules must not depend on the API layer; move shared code into src/: {offenders}"
    )
