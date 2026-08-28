"""DIM CSV ingestion.

Columns are always accessed by header name, never by position — DIM's export
format gains/loses/reorders columns between releases. `load_*` fails loudly if
a column we depend on has vanished.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd


class SchemaError(ValueError):
    """The CSV doesn't look like the DIM export we expect."""


class ExportDecodeError(ValueError):
    """A byte-backed DIM export is not valid UTF-8.

    Byte loaders decode strictly before handing content to pandas. A separate
    exception lets upload callers report malformed bytes independently from a
    validly decoded export with an invalid schema.
    """


# The minimal set of columns the pipeline relies on. Everything else in the
# export is carried along untouched but never assumed to exist.
REQUIRED_BASE_COLUMNS = frozenset(
    {"Name", "Hash", "Id", "Tag", "Rarity", "Locked", "Equipped", "Notes"}
)
# Ammo is weapons-only: it keeps an armor export (which also has Type) from
# silently loading through the weapons path. Crafted fields feed the hard
# safety rail and are therefore part of the required safety-critical schema.
REQUIRED_WEAPON_COLUMNS = REQUIRED_BASE_COLUMNS | {
    "Type", "Ammo", "Crafted", "Crafted Level"
}
# Ghost exports have no Type column. Loadouts is required because loadout
# membership is a keep signal in the ghost cleanup pass.
REQUIRED_GHOST_COLUMNS = REQUIRED_BASE_COLUMNS | {"Loadouts"}

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

# Beyond the scoring columns, the armor dupe passes need: Loadouts (loadout
# membership keeps a piece, as in the ghost pass), the fingerprint columns
# (Tuning Stat / Seasonal Mod / Holofoil — roll identity, see
# rules/armor_dupes.py), the survivor-ranking columns (Masterwork Tier,
# Power), Tier (the close pass never compares across gear tiers), Perks 0 —
# the Spirit perks in the Perks columns are the roll identity for exotic
# class items, so their wholesale disappearance must not silently merge
# distinct rolls — and Archetype (the score pass's last-of-kind guard keys
# on it; empty cells are valid — legacy pieces have no archetype). Required
# so a renamed column fails loudly.
REQUIRED_ARMOR_COLUMNS = (
    REQUIRED_BASE_COLUMNS
    | {"Type", "Equippable", "Loadouts", "Tuning Stat", "Seasonal Mod",
       "Holofoil", "Masterwork Tier", "Power", "Tier", "Perks 0", "Archetype"}
    | set(ARMOR_STATS.values())
)


def _strip_dim_id_quotes(series: pd.Series) -> pd.Series:
    # DIM wraps the 64-bit instance id in literal quotes ("""123""" in the raw
    # file) so spreadsheets don't truncate it to a float. Store it bare.
    return series.str.strip('"')


def _validate_dim_csv(
    df: pd.DataFrame,
    required: frozenset[str],
    kind: str,
    display_label: str,
) -> pd.DataFrame:
    missing = required - set(df.columns)
    if missing:
        raise SchemaError(
            f"{display_label}: missing expected DIM columns {sorted(missing)} — "
            f"the export format may have changed, or this isn't a {kind} export."
        )

    df["Id"] = _strip_dim_id_quotes(df["Id"])
    if df["Id"].duplicated().any():
        dupes = df.loc[df["Id"].duplicated(), "Id"].tolist()
        raise SchemaError(
            f"{display_label}: duplicate instance ids {dupes[:5]} — corrupt export?"
        )
    return df


def _load_dim_csv(
    source: str | Path | StringIO,
    required: frozenset[str],
    kind: str,
    display_label: str,
) -> pd.DataFrame:
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    return _validate_dim_csv(df, required, kind, display_label)


def _decode_export_bytes(content: bytes, display_label: str) -> StringIO:
    try:
        # Keep a leading BOM in the decoded text. pandas accepts it at the
        # start of the first header, matching the path loader's behavior.
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExportDecodeError(f"{display_label}: invalid UTF-8") from exc
    return StringIO(text)


def _load_dim_bytes(
    content: bytes,
    required: frozenset[str],
    kind: str,
    display_label: str,
) -> pd.DataFrame:
    source = _decode_export_bytes(content, display_label)
    return _load_dim_csv(source, required, kind, display_label)


def is_crafted(value: object) -> bool:
    """Interpret DIM's enum-like ``Crafted`` field.

    DIM exports crafted weapons as ``crafted`` and ordinary weapons as
    ``false``. Empty values are also an explicit not-crafted value for older
    or shared exports. Unknown non-empty values are malformed safety data and
    must not silently disable the crafted-level hard rail.
    """
    normalized = str(value).strip().lower()
    if normalized in {"", "false"}:
        return False
    if normalized == "crafted":
        return True
    raise SchemaError(f"unknown DIM Crafted value {value!r}")


def _validate_weapons(df: pd.DataFrame, display_label: str) -> pd.DataFrame:
    """Validate crafted-state tokens before weapon rules can run."""
    for _, row in df.iterrows():
        try:
            is_crafted(row["Crafted"])
        except SchemaError as exc:
            raise SchemaError(
                f"{display_label}: malformed 'Crafted' value "
                f"{row['Crafted']!r} on {row['Name']} (id {row['Id']}) — {exc}"
            ) from exc
    return df


def load_weapons(path: str | Path) -> pd.DataFrame:
    """Load a DIM weapons export. All columns come back as strings; empty
    cells are empty strings, not NaN."""
    path = Path(path)
    return _validate_weapons(
        _load_dim_csv(path, REQUIRED_WEAPON_COLUMNS, "weapons", str(path)),
        str(path),
    )


def load_weapons_bytes(content: bytes) -> pd.DataFrame:
    """Load a DIM weapons export from strict UTF-8 bytes."""
    return _validate_weapons(
        _load_dim_bytes(content, REQUIRED_WEAPON_COLUMNS, "weapons", "weapons export"),
        "weapons export",
    )


def load_ghosts(path: str | Path) -> pd.DataFrame:
    """Load a DIM ghost export. Same string/empty-cell semantics as weapons."""
    path = Path(path)
    return _load_dim_csv(path, REQUIRED_GHOST_COLUMNS, "ghost", str(path))


def load_ghosts_bytes(content: bytes) -> pd.DataFrame:
    """Load a DIM ghost export from strict UTF-8 bytes."""
    return _load_dim_bytes(content, REQUIRED_GHOST_COLUMNS, "ghost", "ghosts export")


def _validate_armor(df: pd.DataFrame, display_label: str) -> pd.DataFrame:
    """Validate armor stats and ranking fields using a source display label."""
    for col in ARMOR_STATS.values():
        bad = ~df[col].str.strip().str.fullmatch(r"\d+")  # non-negative integers only
        if bad.any():
            offender = df.loc[bad].iloc[0]
            raise SchemaError(
                f"{display_label}: non-numeric {col!r} value {offender[col]!r} on "
                f"{offender['Name']} (id {offender['Id']}) — refusing to score "
                f"armor with malformed stats."
            )
    # Survivor ranking (dupe pass) reads these via to_int, which coerces
    # garbage to 0 and could silently flip which copy survives. Digits when
    # present; empty stays legitimate ("unmasterworked" — strict \d+ was the
    # ghost-pass mistake, it rejects real exports of retired systems).
    for col in ("Masterwork Tier", "Power"):
        bad = ~df[col].str.strip().str.fullmatch(r"\d*")
        if bad.any():
            offender = df.loc[bad].iloc[0]
            raise SchemaError(
                f"{display_label}: malformed {col!r} value {offender[col]!r} on "
                f"{offender['Name']} (id {offender['Id']}) — refusing to rank "
                f"dupe survivors on corrupt data."
            )
    return df


def load_armor(path: str | Path) -> pd.DataFrame:
    """Load a DIM armor export. Same string/empty-cell semantics as weapons.

    Stat cells are validated here: scoring junks pieces by these numbers, so
    a malformed cell silently becoming 0 could junk a best-in-slot piece.
    Fail loudly instead (PLAN.md risks)."""
    path = Path(path)
    return _validate_armor(
        _load_dim_csv(path, REQUIRED_ARMOR_COLUMNS, "armor", str(path)),
        str(path),
    )


def load_armor_bytes(content: bytes) -> pd.DataFrame:
    """Load a DIM armor export from strict UTF-8 bytes."""
    label = "armor export"
    return _validate_armor(
        _load_dim_bytes(content, REQUIRED_ARMOR_COLUMNS, "armor", label),
        label,
    )
