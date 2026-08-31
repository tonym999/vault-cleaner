"""Weapon exact-roll duplicate resolver (PLAN.md rule 3).

DIM's weapon export flattens the frame and randomized socket options into
named ``Perks N`` fields, followed by a tracker socket and mutable current
state (origin/current socket choices, mods, masterwork, memento, and similar
fields). The 2026-08-29 measurement found that the first ``Kill Tracker`` or
``Crucible Tracker`` cell is a stable structural boundary. Those are the only
measured boundary labels: they are compared case-insensitively after removing
one trailing DIM-selected ``*`` marker. Unknown or future names that merely
end in ``Tracker`` remain identity cells when a later measured boundary is
present, and make a row ungroupable when no measured boundary exists. The
exact-roll fingerprint therefore contains the normalized cells before that
boundary. A leading literal ``Enhanced`` followed by one separator space is
retained as part of the perk name: measurement found it on ordinary gameplay
perk names, not as a safe display-only decoration. Perk options remain in
their measured socket order;
no option reordering was observed, so the resolver does not invent
equivalence for an unmeasured reordering. A comma-bearing cell that contains
measured tracker components is also treated as an unmeasured combined tracker
and rejected as ungroupable; legitimate comma-bearing ordinary perk names
remain whole identity cells.

Exotic rows in that export also carry a measured pre-tracker prefix; their
Hash alone is not a safe identity. A row with an unknown/incomplete identity
is ungroupable and never enters automatic duplicate cleanup. Hash remains
part of the grouping key (never Name): the same weapon name can exist under
different hashes across seasonal reissues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from vault_cleaner.duplicate_reference import weapon_reference
from vault_cleaner.note_history import append_tool_clause
from vault_cleaner.rules import rails

# Ranking order per PLAN.md: gear tier > masterwork tier > crafted level > stat
# total. Stat total is an exact-roll-group tiebreaker only, so cross-roll
# comparison never happens; opaque Id breaks ties deterministically.
RANK_COLUMNS = ["Tier", "Masterwork Tier", "Crafted Level"]

STAT_COLUMNS = [
    "Impact", "Range", "Stability", "Handling", "Reload", "Mag", "AA",
    "Zoom", "Airborne Effectiveness", "Velocity", "Blast Radius", "ROF",
    "Accuracy", "Guard Resistance", "Guard Endurance", "Swing Speed",
]

# The export's named fields, rather than dataframe positions, are the
# weapon-roll prefix. ``Perks 0`` is the frame; later cells contain available
# options for randomized sockets. The parser requires only ``Perks 0`` and
# the row-level extractor discovers the contiguous named range present in each
# export to reach the tracker boundary without assuming a fixed width.
_PERK_HEADER = re.compile(r"^Perks ([0-9]+)$")

# These are the only structural boundary labels measured in the export. Do
# not infer a boundary from arbitrary gameplay names ending in "Tracker";
# unknown/future labels must remain identity cells or make the row ungroupable.
_MEASURED_TRACKER_LABELS = frozenset({"kill tracker", "crucible tracker"})


def _has_comma_tracker_candidate(value: str) -> bool:
    """Reject unmeasured combined tracker labels without splitting identity."""
    return "," in value and any(
        _normalize_roll_cell(component) in _MEASURED_TRACKER_LABELS
        for component in value.split(",")
    )


def _normalize_roll_cell(value: object) -> str:
    """Canonicalize one measured immutable perk cell."""
    cell = str(value).strip()
    if cell.endswith("*"):
        cell = cell[:-1].rstrip()
    return cell.casefold()


def _display_roll_cell(value: object) -> str:
    cell = str(value).strip()
    if cell.endswith("*"):
        cell = cell[:-1].rstrip()
    return cell


def _exact_roll_prefix_parts(row) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Return source-facing and normalized values for one measured prefix.

    Legendary and exotic rows use the complete non-empty prefix before the
    first measured ``Kill Tracker`` or ``Crucible Tracker`` cell (after the
    same normalization described above). Cells at and after that boundary are
    mutable current state and excluded. Optional trailing perk cells are
    therefore not mistaken for missing identity. Other rarities, blank hashes,
    missing measured boundaries, gapped/truncated headers, and incomplete
    prefixes fail safe.
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
        or numbers != tuple(range(numbers[-1] + 1))
    ):
        return None
    raw_values = tuple(str(row[column]).strip() for column in columns)
    values = tuple(_normalize_roll_cell(value) for value in raw_values)
    tracker_index = next(
        (
            index
            for index, value in enumerate(values[1:], start=1)
            if value in _MEASURED_TRACKER_LABELS
        ),
        None,
    )
    if tracker_index is None:
        return None
    # Commas are legitimate inside ordinary perk names, so the fingerprint
    # never splits them. Before the first boundary, however, a comma-bearing
    # tracker candidate is an unmeasured combined-cell representation; reject
    # the row regardless of which tracker component appears last.
    if any(_has_comma_tracker_candidate(value) for value in values[:tracker_index]):
        return None
    prefix = values[:tracker_index]
    if not prefix or any(not value for value in prefix):
        return None
    display_values = tuple(_display_roll_cell(value) for value in raw_values)
    return display_values[:tracker_index], prefix


def exact_roll_fingerprint(row) -> tuple[str, ...] | None:
    """Return the measured immutable roll key, or ``None`` if ungroupable."""
    parts = _exact_roll_prefix_parts(row)
    return None if parts is None else parts[1]


def exact_roll_display_prefix(row) -> tuple[str, ...]:
    """Return source-facing names from the proven exact-roll prefix.

    This is presentation-only: the grouping contract remains the normalized
    tuple returned by :func:`exact_roll_fingerprint`.  Reuse that function to
    prove the row is groupable, then retain the source casing and measured
    order for a concise label.
    """
    parts = _exact_roll_prefix_parts(row)
    return () if parts is None else parts[0]


def _winner_reason(best_key: tuple, loser_key: tuple) -> str:
    labels = (
        "higher Tier",
        "higher Masterwork Tier",
        "higher Crafted Level",
        "higher stat total",
    )
    for index, label in enumerate(labels):
        if best_key[index] != loser_key[index]:
            return label
    return "deterministic id tie-break"


@dataclass
class Decision:
    id: str
    hash: str
    name: str
    location: str
    guardian_class: str
    action: str  # "junk" | "review"
    tag: str  # what the output row will carry
    note: str  # user Notes plus the current generated clause
    kept_id: str  # the surviving copy this one lost (or tied) against


def rank_key(row) -> tuple:
    ranks = tuple(rails.to_int(row.get(c)) for c in RANK_COLUMNS)
    stat_total = sum(rails.to_int(row.get(c)) for c in STAT_COLUMNS)
    return (*ranks, stat_total)


def resolve(
    weapons: pd.DataFrame,
    crafted_level_protect: int,
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
            ((rank_key(row), row) for row in group),
            key=lambda kr: str(kr[1]["Id"]),
        )
        keyed = sorted(keyed, key=lambda kr: kr[0], reverse=True)
        best_key, best = keyed[0]
        survivor_group_ids = tuple(
            candidate["Id"] for candidate in group if candidate["Id"] != best["Id"]
        )
        for key, row in keyed[1:]:
            level, reason = rails.protection(row, crafted_level_protect)
            if level == rails.HARD:
                continue
            # A tied copy isn't worse, just redundant — say so honestly.
            rel = "dupe-tie" if key == best_key else "dupe-lower"
            if level == rails.SOFT:
                action = "review"
                tag = row["Tag"]  # preserve whatever tag it has — import must not change it
                hashtag = (
                    f"#vc-review: {rel} ({reason}); keep "
                    f"{weapon_reference(best, exact_roll_display_prefix(best), distinguish_from=survivor_group_ids)}; "
                    f"winner {_winner_reason(best_key, key)}"
                )
            else:
                action = "junk"
                tag = "junk"
                hashtag = (
                    f"#vc-junk: {rel}; keep "
                    f"{weapon_reference(best, exact_roll_display_prefix(best), distinguish_from=survivor_group_ids)}; "
                    f"winner {_winner_reason(best_key, key)}"
                )
            note = append_tool_clause(row["Notes"], hashtag)
            decisions.append(
                Decision(
                    id=row["Id"], hash=row["Hash"], name=row["Name"],
                    location=row.get("Owner", ""), guardian_class="",
                    action=action, tag=tag,
                    note=note, kept_id=best["Id"],
                )
            )
    return decisions
