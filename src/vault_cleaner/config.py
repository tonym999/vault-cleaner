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
        "manifest_cache_dir": "data/cache",
    },
    "wishlists": {
        "max_age_days": 7,
        "sources": {},
    },
    "manifest": {
        "max_age_days": 30,
    },
    "armor": {
        "top_n_per_slot": 5,
        "score_floor": 65,
        "set_bonus": 10,
        "favored_set_perks": [],
        "archetypes": {
            "melee_primary": {
                "weights": {
                    "melee": 3.0, "health": 1.5, "class": 1.0,
                    "grenade": 1.0, "super": 0.5, "weapons": 0.5,
                }
            },
        },
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
