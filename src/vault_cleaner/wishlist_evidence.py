"""Item-level wishlist evidence queries.

Absence, uncovered families, stale sources, and unknown tiers are uncertainty,
never trash evidence; supporting evidence is counted by family, never by source.
"""

from __future__ import annotations

from dataclasses import dataclass

from vault_cleaner.wishlist import (
    TIER_ORDER,
    WishlistEntry,
    WishlistEvidenceSet,
)


@dataclass(frozen=True)
class EvidenceConflict:
    kind: str  # "keep-trash-cross-family" | "keep-trash-same-family" | "tier-disagreement"
    families: tuple[str, ...]  # sorted, unique
    tiers: tuple[str, ...] = ()  # sorted in S..F order; only for tier-disagreement


@dataclass(frozen=True)
class ItemEvidence:
    item_hash: int
    keep_matches: tuple[WishlistEntry, ...]  # source order, then file order
    trash_matches: tuple[WishlistEntry, ...]
    trash_kind: str | None  # "whole-item" | "roll" | None — same result as weapons.trash_match
    keep_families: tuple[str, ...]  # sorted unique families with a keep match
    trash_families: tuple[str, ...]
    covered_families: tuple[str, ...]  # families with ANY entry for item_hash, regardless of perks
    uncovered_families: tuple[str, ...]  # configured families with no entry for item_hash
    stale_sources: tuple[str, ...]  # sources whose fetch status is the stale fallback AND that cover item_hash
    tiers_by_family: tuple[tuple[str, tuple[str, ...]], ...]  # every covered family; () means tier unknown
    conflicts: tuple[EvidenceConflict, ...]  # in the kind order above


def item_evidence(
    evidence: WishlistEvidenceSet,
    item_hash: int,
    perk_hashes: frozenset[int],
) -> ItemEvidence:
    merged = evidence.merged
    keep_entries = (merged.keep_evidence or {}).get(item_hash, [])
    trash_entries = (merged.trash_evidence or {}).get(item_hash, [])

    keep_matches = tuple(e for e in keep_entries if e.perks <= perk_hashes)
    trash_matches = tuple(e for e in trash_entries if (not e.perks or e.perks <= perk_hashes))

    trash_kind: str | None = None
    if trash_matches:
        trash_kind = "whole-item" if not trash_matches[0].perks else "roll"

    keep_families = tuple(sorted({e.family for e in keep_matches}))
    trash_families = tuple(sorted({e.family for e in trash_matches}))

    configured_families: list[str] = []
    seen_fams = set()
    for s in evidence.statuses:
        fam = s.spec.family
        if fam not in seen_fams:
            seen_fams.add(fam)
            configured_families.append(fam)

    all_entries = keep_entries + trash_entries
    covered_fams_set = {e.family for e in all_entries}
    covered_families = tuple(sorted(covered_fams_set))
    uncovered_families = tuple(sorted(fam for fam in configured_families if fam not in covered_fams_set))

    covered_sources = {e.source for e in all_entries}
    stale_sources = tuple(
        sorted(
            s.spec.name
            for s in evidence.statuses
            if s.spec.name in covered_sources and s.fetch.status == "stale-cache-after-failed-download"
        )
    )

    tiers_by_family_list: list[tuple[str, tuple[str, ...]]] = []
    for fam in covered_families:
        distinct_tiers = {
            e.tier
            for e in all_entries
            if e.family == fam and e.tier is not None and e.tier_status == "parsed"
        }
        sorted_tiers = tuple(sorted(distinct_tiers, key=lambda t: TIER_ORDER.get(t, 99)))
        tiers_by_family_list.append((fam, sorted_tiers))
    tiers_by_family = tuple(tiers_by_family_list)

    conflicts: list[EvidenceConflict] = []
    # 1. keep-trash-cross-family: some keep family differs from some trash family
    if keep_families and trash_families and any(kf != tf for kf in keep_families for tf in trash_families):
        cross_fams = tuple(sorted(set(keep_families) | set(trash_families)))
        conflicts.append(
            EvidenceConflict(kind="keep-trash-cross-family", families=cross_fams)
        )

    # 2. keep-trash-same-family: one per family present in both keep_families and trash_families
    same_fams = sorted(set(keep_families) & set(trash_families))
    for fam in same_fams:
        conflicts.append(
            EvidenceConflict(kind="keep-trash-same-family", families=(fam,))
        )

    # 3. tier-disagreement: one per covered family whose parsed tiers contain > 1 distinct value
    for fam, sorted_tiers in tiers_by_family:
        if len(sorted_tiers) > 1:
            conflicts.append(
                EvidenceConflict(kind="tier-disagreement", families=(fam,), tiers=sorted_tiers)
            )

    return ItemEvidence(
        item_hash=item_hash,
        keep_matches=keep_matches,
        trash_matches=trash_matches,
        trash_kind=trash_kind,
        keep_families=keep_families,
        trash_families=trash_families,
        covered_families=covered_families,
        uncovered_families=uncovered_families,
        stale_sources=stale_sources,
        tiers_by_family=tiers_by_family,
        conflicts=tuple(conflicts),
    )
