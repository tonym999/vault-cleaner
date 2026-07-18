"""Weapons pipeline: rails → wishlist pass → dupe pass (PLAN.md rules 1–3).

Wishlist semantics (rule 2):
- trash match (whole-item entry, or a roll subset of the item's perks) →
  candidate junk, unless hard-protected or the item also matches a keep roll.
- keep-roll match → protected from wishlist-trash, and prepended to the dupe
  ranking (match count), but NOT blanket keep: dupes among matched copies
  still resolve to the best copy.
"""

from __future__ import annotations

import pandas as pd

from vault_cleaner.rules import dupes, rails
from vault_cleaner.wishlist import Wishlist


def row_perk_hashes(row: pd.Series, perk_map: dict[str, frozenset[int]]) -> frozenset[int]:
    """All perk hashes present on an item, resolved from the Perks N column
    names. A trailing * (DIM's selected/active marker) is stripped; a name
    maps to every hash variant (base + enhanced) sharing it."""
    hashes: set[int] = set()
    for col in row.index:
        if not col.startswith("Perks "):
            continue
        for name in str(row[col]).split(","):
            name = name.strip().removesuffix("*").strip().casefold()
            if name:
                hashes |= perk_map.get(name, frozenset())
    return frozenset(hashes)


def keep_match_count(item_hash: int, perk_hashes: frozenset[int], wl: Wishlist) -> int:
    return sum(1 for roll in wl.keep.get(item_hash, []) if roll <= perk_hashes)


def trash_match(item_hash: int, perk_hashes: frozenset[int], wl: Wishlist) -> str | None:
    for roll in wl.trash.get(item_hash, []):
        if not roll:
            return "whole-item"
        if roll <= perk_hashes:
            return "roll"
    return None


def run(
    weapons: pd.DataFrame,
    wl: Wishlist,
    perk_map: dict[str, frozenset[int]],
    crafted_level_protect: int,
) -> list[dupes.Decision]:
    keep_counts: dict[str, int] = {}
    decisions: list[dupes.Decision] = []
    trash_ids: set[str] = set()
    trash_junk_ids: set[str] = set()

    for _, row in weapons.iterrows():
        item_hash = int(row["Hash"])
        perk_hashes = row_perk_hashes(row, perk_map)
        keep_counts[row["Id"]] = keep_match_count(item_hash, perk_hashes, wl)

        kind = trash_match(item_hash, perk_hashes, wl)
        if kind is None or keep_counts[row["Id"]] > 0:
            continue  # no trash match, or a keep roll outweighs it
        level, reason = rails.protection(row, crafted_level_protect)
        if level == rails.HARD:
            continue
        if level == rails.SOFT:
            action, tag = "review", row["Tag"]
            hashtag = f"#vc-review: wishlist-trash {kind} ({reason})"
        else:
            action, tag = "junk", "junk"
            hashtag = f"#vc-junk: wishlist-trash {kind}"
            trash_junk_ids.add(row["Id"])
        decisions.append(
            dupes.Decision(
                id=row["Id"], hash=row["Hash"], name=row["Name"],
                owner=row.get("Owner", ""), action=action, tag=tag,
                note=f"{row['Notes']} {hashtag}".strip(), kept_id="",
            )
        )
        trash_ids.add(row["Id"])

    # Trash-junked copies are leaving the vault, so they must not compete in
    # dupe resolution — a trash copy winning "best" would junk every clean
    # copy against it. Soft-reviewed trash stays in the pool: it's only
    # flagged, and probably staying.
    pool = weapons[~weapons["Id"].isin(trash_junk_ids)]
    dupe_decisions = dupes.resolve(
        pool, crafted_level_protect,
        wishlist_key=lambda row: keep_counts.get(row["Id"], 0),
    )
    decisions.extend(d for d in dupe_decisions if d.id not in trash_ids)
    return decisions
