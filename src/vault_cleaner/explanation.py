"""Plain-English explanation models and builders for weapon proposals.

This module is presentation-only: it contains no ranking, grouping,
eligibility, or safety-rail logic.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from vault_cleaner.duplicate_reference import safe_fragment, short_id
from vault_cleaner.parse import is_crafted


@dataclass(frozen=True)
class ProposalExplanation:
    label: str  # short per-slug title
    why: str  # one or two sentences
    keep_instead: str  # "" when the reasoning names no retained copy
    gives_up: str
    caveats: tuple[str, ...] = ()


LABELS: dict[str, str] = {
    "dupe-lower": "Duplicate roll, ranked lower",
    "dupe-tie": "Duplicate roll, ranked equal",
    "wishlist-trash whole-item": "Wishlist rates this weapon trash",
    "wishlist-trash roll": "Wishlist rates this roll trash",
    "coverage-dominated by": "Another copy covers its wishlist rolls",
    "coverage-uncovered vs": "No wishlist roll; another copy has some",
}

_DUPE_DIMENSION_MAP = {
    "higher Tier": "a higher Tier",
    "higher Masterwork Tier": "a higher masterwork tier",
    "higher Crafted Level": "a higher crafted level",
    "higher stat total": "a higher stat total",
}


def weapon_keep_reference(
    row,
    perk_prefix: Iterable[str] = (),
    *,
    distinguish_from: Iterable[object] = (),
) -> str:
    """Render a readable retained-weapon reference for explanations."""
    parts: list[str] = []
    sid = short_id(row.get("Id", ""), distinguish_from=distinguish_from)
    owner = safe_fragment(row.get("Owner", ""), escape_structure=False)
    if owner:
        loc = "in the Vault" if owner == "Vault" else f"on {owner}"
        parts.append(f"copy {sid} {loc}")
    else:
        parts.append(f"copy {sid}")

    tier = safe_fragment(row.get("Tier", ""), limit=12, escape_structure=False)
    if tier:
        parts.append(f"Tier {tier}")

    masterwork = safe_fragment(
        row.get("Masterwork Tier", ""), limit=12, escape_structure=False
    )
    if masterwork:
        parts.append(f"masterwork tier {masterwork}")

    crafted = safe_fragment(
        row.get("Crafted Level", ""), limit=12, escape_structure=False
    )
    if is_crafted(row.get("Crafted", "")) and crafted:
        parts.append(f"crafted level {crafted}")

    perks = [
        safe_fragment(perk, escape_structure=False)
        for perk in perk_prefix
        if str(perk).strip()
    ]
    if perks:
        parts.append("roll " + " / ".join(perks[-2:]))

    return ", ".join(parts)


def dupe(
    *, tie: bool, winner: str, keep_instead: str
) -> ProposalExplanation:
    """Build an explanation for an exact-duplicate loser or tie."""
    if tie:
        return ProposalExplanation(
            label=LABELS["dupe-tie"],
            why=(
                "You own another copy with the same perk roll that ranks equal"
                " on Tier, masterwork tier, crafted level and stat total. One"
                " copy is kept, chosen by a fixed ID order."
            ),
            keep_instead=keep_instead,
            gives_up=(
                "Nothing in the perk roll. Kill trackers, mods and mementos"
                " are not compared."
            ),
        )

    if winner not in _DUPE_DIMENSION_MAP:
        raise ValueError(f"unrecognized dupe winner dimension: {winner!r}")

    dimension = _DUPE_DIMENSION_MAP[winner]
    return ProposalExplanation(
        label=LABELS["dupe-lower"],
        why=f"You own another copy with the same perk roll and {dimension}.",
        keep_instead=keep_instead,
        gives_up=(
            "Nothing in the perk roll. Kill trackers, mods and mementos"
            " are not compared."
        ),
    )


def wishlist_trash(
    *,
    whole_item: bool,
    sources: tuple[str, ...] = (),
    pve_only: bool = False,
) -> ProposalExplanation:
    """Build an explanation for a wishlist-trash proposal."""
    if whole_item:
        label = LABELS["wishlist-trash whole-item"]
        base_why = (
            "A wishlist you use rates every roll of this weapon as trash."
        )
    else:
        label = LABELS["wishlist-trash roll"]
        base_why = "A wishlist you use rates this perk roll as trash."

    if sources:
        clean_sources = sorted({
            safe_fragment(s, escape_structure=False)
            for s in sources
            if str(s).strip()
        })
        formatted_sources = ", ".join(clean_sources)
        why = f"{base_why} Source: {formatted_sources}."
    else:
        why = base_why

    caveats = (
        ("That rating is for PvE only and says nothing about PvP use.",)
        if pve_only
        else ()
    )

    return ProposalExplanation(
        label=label,
        why=why,
        keep_instead="",
        gives_up=(
            "This copy. No other copy is named as a replacement; the"
            " suggestion rests on the wishlist rating alone."
        ),
        caveats=caveats,
    )


def coverage_dominated(
    *, n: int, m: int, keep_instead: str
) -> ProposalExplanation:
    """Build an explanation for a coverage-dominated weapon proposal."""
    return ProposalExplanation(
        label=LABELS["coverage-dominated by"],
        why=(
            f"Another copy of this weapon matches every curated wishlist roll"
            f" this one matches, and more ({m} against {n})."
        ),
        keep_instead=keep_instead,
        gives_up=(
            "No wishlist-recommended roll. Perks no wishlist recommends may"
            " differ, so compare them if you use this copy for something"
            " specific."
        ),
    )


def coverage_uncovered(
    *, m: int, keep_instead: str
) -> ProposalExplanation:
    """Build an explanation for an uncovered weapon proposal."""
    curated_str = "1 curated roll" if m == 1 else f"{m} curated rolls"
    return ProposalExplanation(
        label=LABELS["coverage-uncovered vs"],
        why=(
            f"This copy matches no curated wishlist roll, while another copy of"
            f" the same weapon matches {curated_str}."
        ),
        keep_instead=keep_instead,
        gives_up=(
            "No wishlist-recommended roll. Not being on a wishlist does not"
            " make a roll bad, so check it if you use this copy."
        ),
    )


def with_context(
    explanation: ProposalExplanation,
    *,
    action: str,
    protection_level: str | None,
    protection_reason: str,
    locked: bool,
    in_loadout: bool,
    partner_also_proposed: bool,
) -> ProposalExplanation:
    """Return a copy of explanation with context caveats appended."""
    context_caveats: list[str] = []
    if action == "review":
        context_caveats.append(
            "Review only: approving adds a note in DIM and leaves its tag"
            " unchanged."
        )
    if protection_level == "soft" and protection_reason == "exotic":
        context_caveats.append("Exotic, so never tagged junk automatically.")
    if locked:
        context_caveats.append("Locked in game: unlock it before dismantling.")
    if in_loadout:
        context_caveats.append(
            "In a DIM loadout: dismantling it breaks that loadout."
        )
    if partner_also_proposed:
        context_caveats.append(
            "The copy suggested to keep is also proposed in this report. Decide"
            " on both together."
        )

    return replace(
        explanation,
        caveats=explanation.caveats + tuple(context_caveats),
    )
