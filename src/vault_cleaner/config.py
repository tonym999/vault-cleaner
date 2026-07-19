"""Load config.toml with defaults, so a missing file or key never crashes.

Armor settings are validated at load time: a misspelt stat weight or an
empty archetypes table would silently skew every score, and --write exports
those junk decisions — better to refuse loudly.
"""

from __future__ import annotations

import math
import tomllib
from pathlib import Path

from vault_cleaner.parse import ARMOR_STATS

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
    """config.toml is unreadable, malformed, or invalid."""


def _is_number(v: object) -> bool:
    # bool subclasses int; TOML permits nan/inf literals, and NaN silently
    # poisons every score comparison — finite numbers only.
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _validate_armor(cfg: dict) -> None:
    a = cfg["armor"]
    top_n = a.get("top_n_per_slot")
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 0:
        raise ConfigError("armor.top_n_per_slot must be a non-negative integer")
    if not _is_number(a.get("score_floor")):
        raise ConfigError("armor.score_floor must be a finite number")
    if not _is_number(a.get("set_bonus")) or a["set_bonus"] < 0:
        # A negative bonus would penalize the *favored* sets toward junk
        raise ConfigError("armor.set_bonus must be a finite number >= 0")

    favored = a.get("favored_set_perks")
    if not isinstance(favored, list) or any(
        not isinstance(p, str) or not p.strip() for p in favored
    ):
        raise ConfigError(
            "armor.favored_set_perks must be a list of non-empty strings "
            '(e.g. ["Erebos Glance"]), not a bare string'
        )

    archetypes = a.get("archetypes")
    if not isinstance(archetypes, dict) or not archetypes:
        raise ConfigError("armor.archetypes must define at least one archetype")
    for name, spec in archetypes.items():
        where = f"armor.archetypes.{name}"
        if not isinstance(spec, dict) or ("weights" in spec) == ("top_stats" in spec):
            raise ConfigError(f"{where}: define exactly one of 'weights' or 'top_stats'")
        if "top_stats" in spec:
            t = spec["top_stats"]
            if not isinstance(t, int) or isinstance(t, bool) or not 1 <= t <= len(ARMOR_STATS):
                raise ConfigError(f"{where}.top_stats must be an integer in 1..{len(ARMOR_STATS)}")
            continue
        weights = spec["weights"]
        if not isinstance(weights, dict) or not weights:
            raise ConfigError(f"{where}.weights must be a non-empty table")
        unknown = set(weights) - set(ARMOR_STATS)
        if unknown:
            raise ConfigError(
                f"{where}.weights: unknown stat(s) {sorted(unknown)} — valid: {sorted(ARMOR_STATS)}"
            )
        if any(not _is_number(w) or w < 0 for w in weights.values()):
            raise ConfigError(f"{where}.weights values must be numbers >= 0")
        if not any(w > 0 for w in weights.values()):
            raise ConfigError(f"{where}.weights needs at least one positive weight")


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
        value = data.get(section, {})
        if not isinstance(value, dict):
            raise ConfigError(f"{path}: [{section}] must be a table, got {type(value).__name__}")
        merged[section] = {**defaults, **value}
    for section, values in data.items():
        merged.setdefault(section, values)
    _validate_armor(merged)
    return merged
