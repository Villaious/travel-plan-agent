from __future__ import annotations

import os
from pathlib import Path


_ENV_LOADED = False


def load_env(path: str | os.PathLike[str] = ".env") -> None:
    """Load simple KEY=VALUE pairs from a .env file without extra dependencies."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    env_path = Path(path)
    if not env_path.exists():
        _ENV_LOADED = True
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
    _ENV_LOADED = True


def get_env(name: str, default: str = "") -> str:
    load_env()
    return os.getenv(name, default).strip()


def get_bool_env(name: str, default: bool = False) -> bool:
    value = get_env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on", "y"}


def get_float_env(name: str, default: float) -> float:
    value = get_env(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_int_env(name: str, default: int) -> int:
    value = get_env(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default
