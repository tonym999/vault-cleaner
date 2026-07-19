"""DIM CSV ingestion.

Columns are always accessed by header name, never by position — DIM's export
format gains/loses/reorders columns between releases. `load_*` fails loudly if
a column we depend on has vanished.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class SchemaError(ValueError):
    """The CSV doesn't look like the DIM export we expect."""


# The minimal set of columns the pipeline relies on. Everything else in the
# export is carried along untouched but never assumed to exist.
REQUIRED_BASE_COLUMNS = frozenset(
    {"Name", "Hash", "Id", "Tag", "Rarity", "Locked", "Equipped", "Notes"}
)
# Ammo is weapons-only: it keeps an armor export (which also has Type) from
# silently loading through the weapons path.
REQUIRED_WEAPON_COLUMNS = REQUIRED_BASE_COLUMNS | {"Type", "Ammo"}
# Ghost cleanup ranks by these. NOTE: current DIM exports leave them EMPTY
# on every shell (ghost energy is a retired system) — empty is the normal
# state and means "no value"; only non-empty garbage is format drift.
GHOST_RANK_COLUMNS = ["Energy Capacity", "Masterwork Tier"]

# Ghost exports have no Type column.
REQUIRED_GHOST_COLUMNS = REQUIRED_BASE_COLUMNS | set(GHOST_RANK_COLUMNS)

# THE armor stat lookup table (PLAN.md risks): canonical stat name → export
# column. If DIM or Armor 3.0 renames a stat, fix it here and only here.
# Scoring uses base stats — mods are removable and shouldn't flatter a piece.
ARMOR_STATS = {
    "weapons": "Weapons (Base)",
    "health": "Health (Base)",
    "class": "Class (Base)",
    "grenade": "Grenade (Base)",
    "super": "Super (Base)",
    "melee": "Melee (Base)",
}

REQUIRED_ARMOR_COLUMNS = (
    REQUIRED_BASE_COLUMNS | {"Type", "Equippable"} | set(ARMOR_STATS.values())
)


def _strip_dim_id_quotes(series: pd.Series) -> pd.Series:
    # DIM wraps the 64-bit instance id in literal quotes ("""123""" in the raw
    # file) so spreadsheets don't truncate it to a float. Store it bare.
    return series.str.strip('"')


def _load_dim_csv(path: str | Path, required: frozenset[str], kind: str) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    missing = required - set(df.columns)
    if missing:
        raise SchemaError(
            f"{path}: missing expected DIM columns {sorted(missing)} — "
            f"the export format may have changed, or this isn't a {kind} export."
        )

    df["Id"] = _strip_dim_id_quotes(df["Id"])
    if df["Id"].duplicated().any():
        dupes = df.loc[df["Id"].duplicated(), "Id"].tolist()
        raise SchemaError(f"{path}: duplicate instance ids {dupes[:5]} — corrupt export?")
    return df


def load_weapons(path: str | Path) -> pd.DataFrame:
    """Load a DIM weapons export. All columns come back as strings; empty
    cells are empty strings, not NaN."""
    return _load_dim_csv(path, REQUIRED_WEAPON_COLUMNS, "weapons")


def load_ghosts(path: str | Path) -> pd.DataFrame:
    """Load a DIM ghost export. Same string/empty-cell semantics as weapons.

    Ranking cells must be empty (the current-export norm) or a non-negative
    integer; anything else would silently rank as 0 and mis-junk shells."""
    df = _load_dim_csv(path, REQUIRED_GHOST_COLUMNS, "ghost")
    for col in GHOST_RANK_COLUMNS:
        bad = ~df[col].str.strip().str.fullmatch(r"\d*")
        if bad.any():
            offender = df.loc[bad].iloc[0]
            raise SchemaError(
                f"{path}: non-numeric {col!r} value {offender[col]!r} on "
                f"{offender['Name']} (id {offender['Id']}) — refusing to rank "
                f"ghosts with malformed cells."
            )
    return df


def load_armor(path: str | Path) -> pd.DataFrame:
    """Load a DIM armor export. Same string/empty-cell semantics as weapons.

    Stat cells are validated here: scoring junks pieces by these numbers, so
    a malformed cell silently becoming 0 could junk a best-in-slot piece.
    Fail loudly instead (PLAN.md risks)."""
    df = _load_dim_csv(path, REQUIRED_ARMOR_COLUMNS, "armor")
    for col in ARMOR_STATS.values():
        bad = ~df[col].str.strip().str.fullmatch(r"\d+")  # non-negative integers only
        if bad.any():
            offender = df.loc[bad].iloc[0]
            raise SchemaError(
                f"{path}: non-numeric {col!r} value {offender[col]!r} on "
                f"{offender['Name']} (id {offender['Id']}) — refusing to score "
                f"armor with malformed stats."
            )
    return df
