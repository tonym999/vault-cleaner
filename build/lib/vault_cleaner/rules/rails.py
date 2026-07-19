"""Safety rails (PLAN.md rule 1) — two tiers of never-junk protection.

hard: the tool never emits an output row for the item at all.
soft: the item is never tagged junk, but dupe passes may attach a
      `#vc-review` note recommending manual review (locked and exotic
      items — the user decides, the tool only points).
"""

from __future__ import annotations

HARD = "hard"
SOFT = "soft"

HARD_PROTECT_TAGS = frozenset({"favorite", "keep", "archive"})


def is_true(value: object) -> bool:
    return str(value).strip().lower() == "true"


def to_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip() or default)
    except ValueError:
        return default


def protection(row, crafted_level_protect: int) -> tuple[str | None, str]:
    """Classify one item row. Returns (HARD|SOFT|None, reason)."""
    tag = row.get("Tag", "")
    if tag in HARD_PROTECT_TAGS:
        return HARD, f"dim-tag:{tag}"
    if is_true(row.get("Equipped", "")):
        return HARD, "equipped"
    if is_true(row.get("Crafted", "")) and to_int(row.get("Crafted Level")) >= crafted_level_protect:
        return HARD, f"crafted-lv{row.get('Crafted Level')}"
    if row.get("Rarity", "") == "Exotic":
        return SOFT, "exotic"
    if is_true(row.get("Locked", "")):
        return SOFT, "locked"
    return None, ""
