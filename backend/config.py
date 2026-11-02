"""Backend configuration facade.

Settings live in :mod:`src.config` so the domain engine never imports the API
layer. This module re-exports the same objects unchanged, which keeps every
existing import (and test that patches ``backend.config.settings``) working:
there is exactly one ``Settings`` instance, reachable under either name.
"""

from __future__ import annotations

from src.config import Settings, redact_secret, sanitize_text, settings

__all__ = ["Settings", "redact_secret", "sanitize_text", "settings"]
