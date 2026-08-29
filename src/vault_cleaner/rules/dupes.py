"""Weapon exact-roll duplicate resolver (PLAN.md rule 3).

DIM's weapon export flattens the frame and randomized socket options into
named ``Perks N`` fields, followed by a tracker socket and mutable current
state (origin/current socket choices, mods, masterwork, memento, and similar
fields). The 2026-08-29 measurement found that the first tracker-labelled
cell is a stable structural boundary. The exact-roll fingerprint therefore
contains the normalized cells before that boundary, with DIM's trailing
selected ``*`` marker and leading ``Enhanced `` decoration removed. Perk
options remain in their measured socket order; no option reordering was
observed, so the resolver does not invent equivalence for an unmeasured
reordering.

Exotic rows in that export also carry a measured pre-tracker prefix; their
Hash alone is not a safe identity. A row with an unknown/incomplete identity
is ungroupable and never enters automatic duplicate cleanup. Hash remains
part of the grouping key (never Name): the same weapon name can exist under
different hashes across seasonal reissues.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from vault_cleaner.rules import rails

# Ranking order per PLAN.md: wishlist match (arrives in M3 via wishlist_key)
# > gear tier > masterwork tier > crafted level > stat total. Stat total is an
# exact-roll-group tiebreaker only, so cross-roll comparison never happens.
RANK_COLUMNS = ["Tier", "Masterwork Tier", "Crafted Level"]

STAT_COLUMNS = [
    "Impact", "Range", "Stability", "Handling", "Reload", "Mag", "AA",
    "Zoom", "Airborne Effectiveness", "Velocity", "Blast Radius", "ROF",
    "Accuracy", "Guard Resistance", "Guard Endurance", "Swing Speed",
]

# The export's named fields, rather than dataframe positions, are the
# measured weapon-roll prefix. ``Perks 0`` is the frame; later cells contain
# available options for randomized sockets. The parser requires the measured
# prefix fields, and the row-level extractor discovers any later named fields
# to reach the tracker boundary without assuming a fixed export width.
_PERK_HEADER = re.compile(r"^Perks ([0-9]+)$")
# The measured export is contiguous through Perks 20. Requiring that lower
# bound prevents a truncated/gapped header set from becoming a partial key;
# later contiguous fields are accepted so the boundary can move with DIM.
_MIN_MEASURED_PERK_INDEX = 20

# Tracker labels are the only structural boundary observed across this
# export. Match the category suffix, rather than a brittle catalogue of
# today's names (Kill Tracker, Crucible Tracker, etc.). Unknown labels do
# not get guessed: without this boundary the row is ungroupable.
_TRACKER_CELL = re.compile(r"(?:^|\s)tracker$", re.IGNORECASE)


def _normalize_roll_cell(value: object) -> str:
    """Canonicalize one measured immutable perk cell."""
    cell = str(value).strip()
    if cell.endswith("*"):
        cell = cell[:-1].rstrip()
    if cell.casefold().startswith("enhanced "):
        cell = cell[len("Enhanced "):].lstrip()
    return cell.casefold()


def exact_roll_fingerprint(row) -> tuple[str, ...] | None:
    """Return the measured immutable roll key, or ``None`` if ungroupable.

    Legendary and exotic rows use the complete non-empty prefix before the
    first tracker-labelled cell. Cells at and after that boundary are mutable
    current state and excluded. Optional trailing perk cells are therefore
    not mistaken for missing identity. Other rarities, blank hashes, missing
    tracker boundaries, gapped/truncated headers, and incomplete prefixes
    fail safe.
    """
    item_hash = str(row.get("Hash", "")).strip()
    if not item_hash:
        return None

    rarity = str(row.get("Rarity", "")).strip().casefold()
    if rarity not in {"legendary", "exotic"}:
        return None

    keys = row.index if hasattr(row, "index") else row.keys()
    columns = sorted(
        (
            column
            for column in keys
            if isinstance(column, str) and _PERK_HEADER.fullmatch(column)
        ),
        key=lambda column: int(_PERK_HEADER.fullmatch(column).group(1)),
    )
    numbers = tuple(
        int(_PERK_HEADER.fullmatch(column).group(1)) for column in columns
    )
    if (
        not columns
        or numbers[0] != 0
        or numbers[-1] < _MIN_MEASURED_PERK_INDEX
        or numbers != tuple(range(numbers[-1] + 1))
    ):
        return None
    values = tuple(_normalize_roll_cell(row[column]) for column in columns)
    tracker_index = next(
        (
            index
            for index, value in enumerate(values[1:], start=1)
            if _TRACKER_CELL.search(value)
        ),
        None,
    )
    if tracker_index is None:
        return None
    prefix = values[:tracker_index]
    if not prefix or any(not value for value in prefix):
        return None
    return prefix


@dataclass
class Decision:
    id: str
    hash: str
    name: str
    owner: str
    action: str  # "junk" | "review"
    tag: str  # what the output row will carry
    note: str  # full Notes cell (existing notes + our hashtag)
    kept_id: str  # the surviving copy this one lost (or tied) against


def rank_key(row, wishlist_key: Callable | None = None) -> tuple:
    wl = wishlist_key(row) if wishlist_key else 0
    ranks = tuple(rails.to_int(row.get(c)) for c in RANK_COLUMNS)
    stat_total = sum(rails.to_int(row.get(c)) for c in STAT_COLUMNS)
    return (wl, *ranks, stat_total)


def resolve(
    weapons: pd.DataFrame,
    crafted_level_protect: int,
    wishlist_key: Callable | None = None,
) -> list[Decision]:
    decisions: list[Decision] = []
    groups: dict[tuple[str, tuple[str, ...]], list] = {}
    for _, row in weapons.iterrows():
        fingerprint = exact_roll_fingerprint(row)
        if fingerprint is None:
            continue
        group_key = (str(row["Hash"]), fingerprint)
        groups.setdefault(group_key, []).append(row)

    # Sort group keys and then rank ties by opaque instance id so both the
    # decision order and the survivor are independent of CSV row order.
    for _, group in sorted(groups.items(), key=lambda item: item[0]):
        if len(group) < 2:
            continue
        keyed = sorted(
            ((rank_key(row, wishlist_key), row) for row in group),
            key=lambda kr: str(kr[1]["Id"]),
        )
        keyed = sorted(keyed, key=lambda kr: kr[0], reverse=True)
        best_key, best = keyed[0]
        for key, row in keyed[1:]:
            level, reason = rails.protection(row, crafted_level_protect)
            if level == rails.HARD:
                continue
            # A tied copy isn't worse, just redundant — say so honestly.
            rel = "dupe-tie" if key == best_key else "dupe-lower"
            if level == rails.SOFT:
                action = "review"
                tag = row["Tag"]  # preserve whatever tag it has — import must not change it
                hashtag = f"#vc-review: {rel} ({reason}), kept {best['Id']}"
            else:
                action = "junk"
                tag = "junk"
                hashtag = f"#vc-junk: {rel}, kept {best['Id']}"
            note = f"{row['Notes']} {hashtag}".strip()
            decisions.append(
                Decision(
                    id=row["Id"], hash=row["Hash"], name=row["Name"],
                    owner=row.get("Owner", ""), action=action, tag=tag,
                    note=note, kept_id=best["Id"],
                )
            )
    return decisions
