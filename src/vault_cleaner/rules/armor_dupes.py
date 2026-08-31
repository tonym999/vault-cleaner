"""Armor exact-dupe pass (#17): one survivor per identical roll.

Fingerprint (identity — same group ⇔ same values): Hash, the six base stats
via ARMOR_STATS, Tuning Stat, Seasonal Mod, Holofoil, and the sorted
"Spirit of ..." perk signature. Everything else on the row is mutable state
(mods, masterwork, power, tags, locks, location) — it decides who survives,
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

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import pandas as pd

from vault_cleaner.duplicate_reference import armor_reference
from vault_cleaner.note_history import append_tool_clause
from vault_cleaner.parse import ARMOR_STATS
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import Decision

SPIRIT_PREFIX = "Spirit of "

# DIM's Type values for class items. Exotic class items are the one armor
# kind whose roll identity lives in the Perks columns (Spirit perks).
CLASS_ITEM_TYPES = frozenset({"Titan Mark", "Warlock Bond", "Hunter Cloak"})

# A complete exotic class item roll carries exactly this many Spirit perks
# (measured: 38/38 real copies). Fewer means the identity is truncated —
# e.g. a Perks column beyond the schema-required Perks 0 vanished — and a
# truncated signature could merge distinct rolls that share their first
# Spirit. Longer can't false-merge anything, so only shorter is rejected.
SPIRIT_ROLL_SIZE = 2


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
    """An exotic class item exporting fewer than SPIRIT_ROLL_SIZE Spirit
    perks is an unknown (or truncated) roll: it can't be proven identical
    to anything, so the dupe passes must not group or compare it.
    (Measured: every real copy shows exactly two spirits, so this only
    fires on data we haven't seen — better silent than wrong.)"""
    return (
        row["Rarity"] == "Exotic"
        and row["Type"] in CLASS_ITEM_TYPES
        and len(spirit_signature(row)) < SPIRIT_ROLL_SIZE
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
    masterwork because it's the owner's explicit lock signal."""
    level, _ = rails.protection(row, crafted_level_protect)
    return (
        level == rails.HARD,
        in_loadout(row),
        rails.is_true(row["Locked"]),
        rails.to_int(row["Masterwork Tier"]),
        rails.to_int(row["Power"]),
    )


def _winner_reason(best_rank: tuple, loser_rank: tuple) -> str:
    labels = (
        "hard protection",
        "loadout membership",
        "lock",
        "higher Masterwork Tier",
        "higher Power",
    )
    for index, label in enumerate(labels):
        if best_rank[index] != loser_rank[index]:
            return label
    return "deterministic id tie-break"


@dataclass(frozen=True)
class ArmorExactDuplicateMember:
    """A stable, read-only projection of one member of an exact group."""

    id: str
    location: str
    protection_level: str | None
    protection_reason: str
    equipped: bool
    in_loadout: bool
    locked: bool
    masterwork_tier: int
    power: int
    disposition: str
    proposal_action: str | None
    proposal_reason: str | None


@dataclass(frozen=True)
class ArmorExactDuplicateGroup:
    """The complete authoritative exact-dupe group for report consumers."""

    group_id: str
    hash: str
    name: str
    type: str
    guardian_class: str
    item_archetype: str
    stats: Mapping[str, int]
    tuning_mod_slot: str
    seasonal_mod: str
    holofoil: str
    spirit_signature: tuple[str, ...]
    preferred_survivor_id: str
    members: tuple[ArmorExactDuplicateMember, ...]


@dataclass(frozen=True)
class ArmorExactDupeAnalysis:
    """One exact-dupe pass result: decisions and their complete groups."""

    decisions: tuple[Decision, ...]
    groups: tuple[ArmorExactDuplicateGroup, ...]


_TUNING_MOD_SLOTS = {
    "weapons": "Weapons",
    "health": "Health",
    "class": "Class",
    "grenade": "Grenade",
    "super": "Super",
    "melee": "Melee",
}
TUNING_MOD_SLOT_UNKNOWN = "none/unknown"
_DISPOSITION_ORDER = {
    "preferred_survivor": 0,
    "retained_protected": 1,
    "proposed_junk": 2,
    "proposed_review": 3,
}


def tuning_mod_slot(value: object) -> str:
    """Label the raw fingerprint tuning value without changing its identity."""
    return _TUNING_MOD_SLOTS.get(str(value).strip().casefold(), TUNING_MOD_SLOT_UNKNOWN)


def _id_order(value: object) -> tuple[int, object]:
    """Order opaque ids like the existing numeric tie-break, with a fallback."""
    raw = str(value)
    try:
        return (0, int(raw))
    except ValueError:
        return (1, raw)


def _member_projection(
    row: pd.Series,
    *,
    level: str | None,
    protection_reason: str,
    disposition: str,
    proposal_action: str | None = None,
    proposal_reason: str | None = None,
) -> ArmorExactDuplicateMember:
    return ArmorExactDuplicateMember(
        id=str(row["Id"]),
        location=str(row.get("Owner", "")),
        protection_level=level,
        protection_reason=str(protection_reason),
        equipped=rails.is_true(row.get("Equipped", "")),
        in_loadout=in_loadout(row),
        locked=rails.is_true(row.get("Locked", "")),
        masterwork_tier=rails.to_int(row["Masterwork Tier"]),
        power=rails.to_int(row["Power"]),
        disposition=disposition,
        proposal_action=proposal_action,
        proposal_reason=proposal_reason,
    )


def _group_projection(
    best: pd.Series,
    group: list[pd.Series],
    members: list[ArmorExactDuplicateMember],
) -> ArmorExactDuplicateGroup:
    # Group identity is member-derived and therefore does not move when
    # mutable ranking fields change.  It is intentionally not Hash/Name:
    # several exact groups can legitimately share either display value.
    group_id = min((str(row["Id"]) for row in group), key=_id_order)
    stats = {
        name: rails.to_int(best[column])
        for name, column in ARMOR_STATS.items()
    }
    return ArmorExactDuplicateGroup(
        group_id=group_id,
        hash=str(best["Hash"]),
        name=str(best["Name"]),
        type=str(best["Type"]),
        guardian_class=str(best.get("Equippable", "")),
        item_archetype=str(best.get("Archetype", "")),
        stats=MappingProxyType(stats),
        tuning_mod_slot=tuning_mod_slot(best["Tuning Stat"]),
        seasonal_mod=str(best["Seasonal Mod"]),
        holofoil=str(best["Holofoil"]),
        spirit_signature=spirit_signature(best),
        preferred_survivor_id=str(best["Id"]),
        members=tuple(
            sorted(
                members,
                key=lambda member: (
                    _DISPOSITION_ORDER[member.disposition],
                    _id_order(member.id),
                ),
            )
        ),
    )


def analyse(armor: pd.DataFrame, crafted_level_protect: int) -> ArmorExactDupeAnalysis:
    """Run the exact pass once and return decisions plus complete groups."""
    decisions: list[Decision] = []
    exact_groups: list[ArmorExactDuplicateGroup] = []
    groups: dict[tuple, list[pd.Series]] = {}
    for _, row in armor.iterrows():
        if unknown_spirit_roll(row):
            continue
        groups.setdefault(fingerprint(row), []).append(row)

    # Group and member order must not depend on the incoming CSV order.  The
    # key deliberately includes the existing fingerprint (including Hash),
    # while the member-derived id makes the ordering easy for consumers to
    # reason about and keeps group ids stable across mutable rank changes.
    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (
            str(group[0]["Hash"]),
            min((str(row["Id"]) for row in group), key=_id_order),
        ),
    )
    for group in ordered_groups:
        if len(group) < 2:
            continue
        # int(Id) tie-break, not row position: reordering the CSV must never
        # change the survivor.
        keyed = sorted(
            group,
            key=lambda r: (
                _survivor_rank(r, crafted_level_protect),
                -int(r["Id"]),
            ),
            reverse=True,
        )
        best = keyed[0]
        best_rank = _survivor_rank(best, crafted_level_protect)
        survivor_group_ids = tuple(
            sorted(
                (str(candidate["Id"]) for candidate in group if candidate["Id"] != best["Id"]),
                key=_id_order,
            )
        )
        best_level, best_reason = rails.protection(best, crafted_level_protect)
        member_projections = [
            _member_projection(
                best,
                level=best_level,
                protection_reason=best_reason,
                disposition="preferred_survivor",
            )
        ]
        for row in keyed[1:]:
            if row["Id"] == best["Id"]:
                continue
            level, reason = rails.protection(row, crafted_level_protect)
            if level == rails.HARD:
                member_projections.append(
                    _member_projection(
                        row,
                        level=level,
                        protection_reason=reason,
                        disposition="retained_protected",
                    )
                )
                continue
            rank = _survivor_rank(row, crafted_level_protect)
            rel = "armor-exact-dupe-tie" if rank == best_rank else "armor-exact-dupe"
            if in_loadout(row):
                # Never junk a loadout member even when a twin survives:
                # the loadout references this exact instance id.
                action, tag = "review", row["Tag"]
                hashtag = (
                    f"#vc-review: {rel} (loadout); keep "
                    f"{armor_reference(best, spirit_signature(best), distinguish_from=survivor_group_ids)}; winner "
                    f"{_winner_reason(best_rank, rank)}"
                )
            elif level == rails.SOFT:
                action, tag = "review", row["Tag"]
                hashtag = (
                    f"#vc-review: {rel} ({reason}); keep "
                    f"{armor_reference(best, spirit_signature(best), distinguish_from=survivor_group_ids)}; winner "
                    f"{_winner_reason(best_rank, rank)}"
                )
            else:
                action, tag = "junk", "junk"
                hashtag = (
                    f"#vc-junk: {rel}; keep "
                    f"{armor_reference(best, spirit_signature(best), distinguish_from=survivor_group_ids)}; winner "
                    f"{_winner_reason(best_rank, rank)}"
                )
            member_projections.append(
                _member_projection(
                    row,
                    level=level,
                    protection_reason=reason,
                    disposition=(
                        "proposed_review" if action == "review" else "proposed_junk"
                    ),
                    proposal_action=action,
                    proposal_reason=rel,
                )
            )
            decisions.append(
                Decision(
                    id=row["Id"], hash=row["Hash"], name=row["Name"],
                    location=row.get("Owner", ""),
                    guardian_class=row.get("Equippable", ""),
                    action=action, tag=tag,
                    note=append_tool_clause(row["Notes"], hashtag),
                    kept_id=best["Id"],
                )
            )
        exact_groups.append(_group_projection(best, group, member_projections))

    return ArmorExactDupeAnalysis(
        decisions=tuple(decisions),
        groups=tuple(exact_groups),
    )


def run(armor: pd.DataFrame, crafted_level_protect: int) -> list[Decision]:
    """Compatibility wrapper returning only the existing decisions."""
    return list(analyse(armor, crafted_level_protect).decisions)
