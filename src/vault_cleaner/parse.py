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
REQUIRED_WEAPON_COLUMNS = frozenset(
    {"Name", "Hash", "Id", "Tag", "Rarity", "Type", "Locked", "Equipped", "Notes"}
)


def _strip_dim_id_quotes(series: pd.Series) -> pd.Series:
    # DIM wraps the 64-bit instance id in literal quotes ("""123""" in the raw
    # file) so spreadsheets don't truncate it to a float. Store it bare.
    return series.str.strip('"')


def load_weapons(path: str | Path) -> pd.DataFrame:
    """Load a DIM weapons export. All columns come back as strings; empty
    cells are empty strings, not NaN."""
    path = Path(path)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    missing = REQUIRED_WEAPON_COLUMNS - set(df.columns)
    if missing:
        raise SchemaError(
            f"{path}: missing expected DIM columns {sorted(missing)} — "
            f"the export format may have changed, or this isn't a weapons export."
        )

    df["Id"] = _strip_dim_id_quotes(df["Id"])
    if df["Id"].duplicated().any():
        dupes = df.loc[df["Id"].duplicated(), "Id"].tolist()
        raise SchemaError(f"{path}: duplicate instance ids {dupes[:5]} — corrupt export?")
    return df
