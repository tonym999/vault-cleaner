"""Safety rails (PLAN.md rule 1) — two tiers of never-junk protection.

hard: the tool never emits an output row for the item at all.
soft: the item is never tagged junk, but dupe passes may attach a
      `#vc-review` note recommending manual review (locked and exotic
      items — the user decides, the tool only points).
"""

from __future__ import annotations

from vault_cleaner.parse import is_crafted, parse_crafted_level

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
    """Classify one item row, propagating malformed safety-field errors.

    ``Crafted`` and ``Crafted Level`` are validated eagerly through the
    parsing-boundary helper before any rail precedence is applied. A crafted
    row with an empty level is an unknown safety value and is hard-protected
    with ``crafted-lvunknown``. Other malformed direct-call data raises
    :class:`SchemaError`; valid rows return ``(HARD|SOFT|None, reason)``.
    """
    crafted = is_crafted(row.get("Crafted", ""))
    crafted_level = parse_crafted_level(
        row.get("Crafted Level", ""), crafted
    )
    tag = row.get("Tag", "")
    if tag in HARD_PROTECT_TAGS:
        return HARD, f"dim-tag:{tag}"
    if is_true(row.get("Equipped", "")):
        return HARD, "equipped"
    if crafted and crafted_level is None:
        return HARD, "crafted-lvunknown"
    if crafted and crafted_level >= crafted_level_protect:
        return HARD, f"crafted-lv{row.get('Crafted Level')}"
    if row.get("Rarity", "") == "Exotic":
        return SOFT, "exotic"
    if is_true(row.get("Locked", "")):
        return SOFT, "locked"
    return None, ""
