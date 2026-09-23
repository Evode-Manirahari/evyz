"""Read a provider token from the environment or a local .env file."""

from __future__ import annotations

import os
from pathlib import Path


def read_secret(root: Path, name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    env_path = root / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        if key.strip() == name:
            found = raw.strip().strip('"').strip("'")
            if found:
                return found
    return None
