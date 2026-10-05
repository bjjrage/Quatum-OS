"""Credential loader for Quant OS.

Secrets never live in source code. Resolution order:
1. Process environment variable.
2. Repository-local .env file (git-ignored).

The loader intentionally does not read config/*_key.txt or other ad-hoc key files.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[2]


def read_env_file(path: Path) -> Dict[str, str]:
    """Parse a small .env file without logging or exposing any values."""
    path = Path(path)
    if not path.exists():
        return {}

    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        out[key] = value

    return out


def get_secret(name: str, root: Optional[Path] = None) -> Optional[str]:
    """Return a secret from the process environment or local .env; never logs it."""
    value = os.environ.get(name)
    if value is not None and value.strip():
        return value.strip()

    base = Path(root) if root is not None else ROOT
    value = read_env_file(base / ".env").get(name)
    return value.strip() if value and value.strip() else None


def describe(value: Optional[str]) -> Dict[str, object]:
    """Return non-sensitive diagnostics suitable for local health endpoints."""
    configured = bool(value)
    return {
        "configured": configured,
        "length": len(value) if value else 0,
        "empieza_con_xai": bool(value and value.startswith("xai-")),
    }
