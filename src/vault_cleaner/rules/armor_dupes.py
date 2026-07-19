"""Armor exact-dupe pass (#17): one survivor per identical roll.

Fingerprint (identity — same group ⇔ same values): Hash, the six base stats
via ARMOR_STATS, Tuning Stat, Seasonal Mod, Holofoil, and the sorted
"Spirit of ..." perk signature. Everything else on the row is mutable state
(mods, masterwork, power, tags, locks, owner) — it decides who survives,
never who matches.

Why exactly these (measured on the real export, #16):

- Tuning Stat is roll identity, not socket state: it's set on tier-5 pieces
  before anything is socketed, and a socketed '+X/-Y' tuning mod always
  matches it. Two rolls differing only in tuning are different pieces.
- Set perks are implied by Hash — every armor set has exactly one item hash
  per class x slot — so no set-perk extraction is needed. The Perks columns
  couldn't provide one anyway: they're a masterwork-gated socket dump, and
  unupgraded copies export almost nothing.
- Tertiary Stat and Archetype are fully derivable from the base stats
  (third-highest stat / top-2 pair), so they'd only duplicate the stats.
- Spirit perks are the one perk-derived identity that matters: exotic class
  item rolls. They're visible on every copy regardless of masterwork.

Survivor selection is deterministic and never depends on CSV row order
(lesson from the ghost-pass reviews): hard-protected > loadout-referenced >
locked > masterwork tier > power, then lowest instance id.
"""

from __future__ import annotations

import pandas as pd

from vault_cleaner.parse import ARMOR_STATS
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import Decision

SPIRIT_PREFIX = "Spirit of "

# DIM's Type values for class items. Exotic class items are the one armor
# kind whose roll identity lives in the Perks columns (Spirit perks).
CLASS_ITEM_TYPES = frozenset({"Titan Mark", "Warlock Bond", "Hunter Cloak"})


def spirit_signature(row: pd.Series) -> tuple[str, ...]:
    """Sorted exotic-class-item Spirit perks — roll identity, unlike the
    rest of the Perks columns (swappable mods, masterwork-gated)."""
    spirits = set()
    for col in row.index:
        if not col.startswith("Perks "):
            continue
        for name in str(row[col]).split(","):
            name = name.strip().removesuffix("*").strip()
            if name.startswith(SPIRIT_PREFIX):
                spirits.add(name)
    return tuple(sorted(spirits))


def unknown_spirit_roll(row: pd.Series) -> bool:
    """An exotic class item exporting no Spirit perks is an unknown roll:
    it can't be proven identical to anything, so the dupe passes must not
    group or compare it. (Measured: every real copy shows its spirits, so
    this only fires on data we haven't seen — better silent than wrong.)"""
    return (
        row["Rarity"] == "Exotic"
        and row["Type"] in CLASS_ITEM_TYPES
        and not spirit_signature(row)
    )


def fingerprint(row: pd.Series) -> tuple:
    stats = tuple(rails.to_int(row[col]) for col in ARMOR_STATS.values())
    return (
        row["Hash"],
        stats,
        row["Tuning Stat"],
        row["Seasonal Mod"],
        row["Holofoil"],
        spirit_signature(row),
    )


def in_loadout(row: pd.Series) -> bool:
    return bool(str(row["Loadouts"]).strip())


def _survivor_rank(row: pd.Series, crafted_level_protect: int) -> tuple:
    """Higher wins. DIM loadouts pin instance ids, so a loadout member must
    survive over a plain twin or the loadout breaks; lock outranks
    masterwork because it's the owner's explicit signal."""
    level, _ = rails.protection(row, crafted_level_protect)
    return (
        level == rails.HARD,
        in_loadout(row),
        rails.is_true(row["Locked"]),
        rails.to_int(row["Masterwork Tier"]),
        rails.to_int(row["Power"]),
    )


def run(armor: pd.DataFrame, crafted_level_protect: int) -> list[Decision]:
    decisions: list[Decision] = []
    groups: dict[tuple, list[pd.Series]] = {}
    for _, row in armor.iterrows():
        if unknown_spirit_roll(row):
            continue
        groups.setdefault(fingerprint(row), []).append(row)

    for group in groups.values():
        if len(group) < 2:
            continue
        # int(Id) tie-break, not row position: reordering the CSV must never
        # change the survivor.
        best = max(
            group,
            key=lambda r: (_survivor_rank(r, crafted_level_protect), -int(r["Id"])),
        )
        best_rank = _survivor_rank(best, crafted_level_protect)
        for row in group:
            if row["Id"] == best["Id"]:
                continue
            level, reason = rails.protection(row, crafted_level_protect)
            if level == rails.HARD:
                continue
            rank = _survivor_rank(row, crafted_level_protect)
            rel = "armor-exact-dupe-tie" if rank == best_rank else "armor-exact-dupe"
            if in_loadout(row):
                # Never junk a loadout member even when a twin survives:
                # the loadout references this exact instance id.
                action, tag = "review", row["Tag"]
                hashtag = f"#vc-review: {rel} (loadout), kept {best['Id']}"
            elif level == rails.SOFT:
                action, tag = "review", row["Tag"]
                hashtag = f"#vc-review: {rel} ({reason}), kept {best['Id']}"
            else:
                action, tag = "junk", "junk"
                hashtag = f"#vc-junk: {rel}, kept {best['Id']}"
            decisions.append(
                Decision(
                    id=row["Id"], hash=row["Hash"], name=row["Name"],
                    owner=row.get("Owner", ""), action=action, tag=tag,
                    note=f"{row['Notes']} {hashtag}".strip(), kept_id=best["Id"],
                )
            )
    return decisions
