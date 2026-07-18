"""Weapon dupe resolver (PLAN.md rule 3).

Group strictly by item Hash — never Name: the same weapon name can exist
under different hashes across seasonal reissues, and those are different
weapons. Within a group the best copy survives untouched; lower copies are
tagged junk, or note-flagged for review when soft-protected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from vault_cleaner.rules import rails

# Ranking order per PLAN.md: wishlist match (arrives in M3 via wishlist_key)
# > gear tier > masterwork tier > crafted level > stat total. Stat total is a
# same-hash tiebreaker only, so cross-archetype comparison never happens.
RANK_COLUMNS = ["Tier", "Masterwork Tier", "Crafted Level"]

STAT_COLUMNS = [
    "Impact", "Range", "Stability", "Handling", "Reload", "Mag", "AA",
    "Zoom", "Airborne Effectiveness", "Velocity", "Blast Radius", "ROF",
    "Accuracy", "Guard Resistance", "Guard Endurance", "Swing Speed",
]


@dataclass
class Decision:
    id: str
    hash: str
    name: str
    owner: str
    action: str  # "junk" | "review"
    tag: str  # what the output row will carry
    note: str  # full Notes cell (existing notes + our hashtag)
    best_id: str  # the copy that outranked this one


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
    for _, group in weapons.groupby("Hash", sort=False):
        if len(group) < 2:
            continue
        copies = sorted(
            (row for _, row in group.iterrows()),
            key=lambda r: rank_key(r, wishlist_key),
            reverse=True,
        )
        best = copies[0]
        for row in copies[1:]:
            level, reason = rails.protection(row, crafted_level_protect)
            if level == rails.HARD:
                continue
            if level == rails.SOFT:
                action = "review"
                tag = row["Tag"]  # preserve whatever tag it has — import must not change it
                hashtag = f"#vc-review: dupe-lower ({reason}), best {best['Id']}"
            else:
                action = "junk"
                tag = "junk"
                hashtag = f"#vc-junk: dupe-lower, best {best['Id']}"
            note = f"{row['Notes']} {hashtag}".strip()
            decisions.append(
                Decision(
                    id=row["Id"], hash=row["Hash"], name=row["Name"],
                    owner=row.get("Owner", ""), action=action, tag=tag,
                    note=note, best_id=best["Id"],
                )
            )
    return decisions
