"""Load config.toml with defaults, so a missing file or key never crashes."""

from __future__ import annotations

import tomllib
from pathlib import Path

DEFAULTS = {
    "rails": {
        "crafted_level_protect": 10,
    },
}


def load_config(path: str | Path = "config.toml") -> dict:
    path = Path(path)
    data: dict = {}
    if path.exists():
        with path.open("rb") as f:
            data = tomllib.load(f)
    merged = {}
    for section, defaults in DEFAULTS.items():
        merged[section] = {**defaults, **data.get(section, {})}
    for section, values in data.items():
        merged.setdefault(section, values)
    return merged
