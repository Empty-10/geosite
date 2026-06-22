"""Lightweight config: load `engine/.env` (if present) and expose settings.

A tiny dotenv reader so we don't add a dependency. Real environment variables always win
over the file, so CI/containers can inject secrets without a `.env`. The file is gitignored
and must never be committed — see `.env.example` for the template.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"  # engine/.env
_loaded = False


def _load_env_once() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    if not _ENV_PATH.exists():
        return
    for raw in _ENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        # setdefault: a real env var takes precedence over the file.
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def get_pagespeed_key() -> str | None:
    """Return the PageSpeed Insights API key, or None if unset (the API works key-less too)."""
    _load_env_once()
    return os.environ.get("PAGESPEED_API_KEY", "").strip() or None
