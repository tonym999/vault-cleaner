"""Load config.toml with defaults, so a missing file or key never crashes."""

from __future__ import annotations

import tomllib
from pathlib import Path

DEFAULTS = {
    "rails": {
        "crafted_level_protect": 10,
    },
    "paths": {
        "input_dir": "data/in",
        "output_dir": "data/out",
        "wishlist_cache_dir": "wishlists",
    },
    "wishlists": {
        "max_age_days": 7,
        "sources": {},
    },
}


class ConfigError(ValueError):
    """config.toml is unreadable or malformed."""


def load_config(path: str | Path = "config.toml") -> dict:
    path = Path(path)
    data: dict = {}
    if path.exists():
        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError) as e:
            raise ConfigError(f"{path}: {e}") from e
    merged = {}
    for section, defaults in DEFAULTS.items():
        merged[section] = {**defaults, **data.get(section, {})}
    for section, values in data.items():
        merged.setdefault(section, values)
    return merged
