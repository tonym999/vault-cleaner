"""Weapon coverage rule pass (PLAN.md rule 4).

Compares distinct rolls of the same item Hash by useful wishlist combination
coverage. Curated keep rolls are author-asserted valid combinations, so
combinations are read from the wishlists rather than enumerated from the export.
Comparison uses the downward-closed uncollapsed matched sets (A strict subset
of B); note explanations display monotonic uncollapsed curated matches (N vs M),
while aggregate CLI counts use subsumption-collapsed maximal combinations.
Absence of coverage is uncertainty, not trash evidence; uncovered copies
receive the distinct 'coverage-uncovered vs' review outcome.

All coverage outcomes are review-only, never junk, and never change existing
tags or bypass safety rails.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

import pandas as pd

from vault_cleaner.duplicate_reference import weapon_reference
from vault_cleaner.explanation import (
    coverage_dominated,
    coverage_uncovered,
    weapon_keep_reference,
)
from vault_cleaner.note_history import append_tool_clause
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import (
    Decision,
    exact_roll_display_prefix,
    exact_roll_fingerprint,
)
from vault_cleaner.rules.id_order import instance_id_order
from vault_cleaner.wishlist import Wishlist


@dataclass(frozen=True)
class CoverageSummary:
    compared_instances: int
    dominated: int
    uncovered: int
    combination_counts: tuple[tuple[int, int], ...]  # (combinations, rows), ascending
    consensus_counts: tuple[tuple[int, int], ...] | None  # (families, combinations); None without evidence


@dataclass(frozen=True)
class CoverageAnalysis:
    decisions: tuple[Decision, ...]
    summary: CoverageSummary


def canonical_perk_tokens(perk_map: dict[str, frozenset[int]]) -> dict[int, int]:
    """Invert PerkMapData.names deterministically to canonical tokens.

    Iterates names in sorted order, uses min(hashes) as the token, and the
    first name wins for a hash appearing under several. A hash absent from
    the returned mapping maps to itself at lookup time.
    """
    tokens: dict[int, int] = {}
    for name in sorted(perk_map):
        hashes = perk_map[name]
        if not hashes:
            continue
        token = min(hashes)
        for perk_hash in hashes:
            tokens.setdefault(perk_hash, token)
    return tokens


def matched_rolls(
    item_hash: int | str,
    perk_hashes: frozenset[int],
    wl: Wishlist,
    tokens: dict[int, int],
) -> frozenset[frozenset[int]]:
    """Return all curated keep rolls matched by perk_hashes, with canonical tokens."""
    raw_rolls = wl.keep.get(int(item_hash), [])
    return frozenset(
        frozenset(tokens.get(p, p) for p in roll)
        for roll in raw_rolls
        if roll <= perk_hashes
    )


def collapse(rolls: frozenset[frozenset[int]]) -> frozenset[frozenset[int]]:
    """Drop recommendations subsumed by a more specific matched one (maximal elements under ⊆)."""
    return frozenset(roll for roll in rolls if not any(roll < other for other in rolls))


def analyse(
    weapons: pd.DataFrame,
    wl: Wishlist,
    perk_map: dict[str, frozenset[int]],
    crafted_level_protect: int,
) -> CoverageAnalysis:
    """Analyse weapon rolls within each Hash group for combination coverage."""
    from vault_cleaner.rules.weapons import row_perk_hashes

    tokens = canonical_perk_tokens(perk_map)

    # 1. Pre-extract facts for each row with a known exact-roll fingerprint.
    rows_facts = []
    for _, row in weapons.iterrows():
        fp = exact_roll_fingerprint(row)
        if fp is None:
            continue
        item_hash = int(row["Hash"])
        perks = row_perk_hashes(row, perk_map)
        matched = matched_rolls(item_hash, perks, wl, tokens)
        level, _ = rails.protection(row, crafted_level_protect)
        rows_facts.append({
            "id": str(row["Id"]),
            "hash": item_hash,
            "row": row,
            "fingerprint": fp,
            "matched": matched,
            "collapsed": collapse(matched),
            "protection_level": level,
        })

    # 2. Group by Hash.
    by_hash: dict[int, list[dict]] = defaultdict(list)
    for facts in rows_facts:
        by_hash[facts["hash"]].append(facts)

    # 3. Filter to multi-roll hashes (Hashes with >= 2 distinct fingerprints).
    multi_roll: dict[int, list[dict]] = {}
    for item_hash in sorted(by_hash):
        members = by_hash[item_hash]
        distinct_fps = {m["fingerprint"] for m in members}
        if len(distinct_fps) >= 2:
            multi_roll[item_hash] = members

    compared = [m for members in multi_roll.values() for m in members]
    compared_instances = len(compared)

    # 4. Compute consensus counts over compared copies if keep_evidence is present.
    family_rolls: dict[int, list[tuple[frozenset[int], str]]] = defaultdict(list)
    if wl.keep_evidence is not None:
        for item_hash, entries in wl.keep_evidence.items():
            for entry in entries:
                canon_roll = frozenset(tokens.get(p, p) for p in entry.perks)
                family_rolls[item_hash].append((canon_roll, entry.family))

    def supporting_families(row_facts: dict, combination: frozenset[int]) -> set[str]:
        return {
            family
            for roll, family in family_rolls[row_facts["hash"]]
            if roll <= combination and roll in row_facts["matched"]
        }

    if wl.keep_evidence is None:
        consensus_counts = None
    else:
        compared_consensus: Counter[int] = Counter()
        for row_facts in compared:
            for comb in row_facts["collapsed"]:
                n_families = len(supporting_families(row_facts, comb))
                compared_consensus[n_families] += 1
        consensus_counts = tuple(sorted(compared_consensus.items()))

    combination_counts = tuple(
        sorted(Counter(len(m["collapsed"]) for m in compared).items())
    )

    # 5. Evaluate pairwise coverage relations.
    decisions: list[Decision] = []
    dominated_count = 0
    uncovered_count = 0

    for item_hash in sorted(multi_roll):
        members = multi_roll[item_hash]
        all_hash_ids = tuple(sorted((m["id"] for m in members), key=instance_id_order))

        for a in members:
            # Hard-protected rows receive no advice, but remain eligible partners.
            if a["protection_level"] == rails.HARD:
                continue

            # Compare only against distinct exact rolls.
            eligible_partners = [
                b for b in members
                if b["id"] != a["id"] and b["fingerprint"] != a["fingerprint"]
            ]

            if len(a["matched"]) > 0:
                # Dominated candidates: matched(A) is a strict subset of matched(B).
                dom_candidates = [
                    (b, len(b["matched"]))
                    for b in eligible_partners
                    if a["matched"] < b["matched"]
                ]
                if dom_candidates:
                    max_gain = max(gain for _, gain in dom_candidates)
                    tied = [b for b, gain in dom_candidates if gain == max_gain]
                    best_b = min(tied, key=lambda b: instance_id_order(b["id"]))
                    partner_reason = (
                        "deterministic id tie-break"
                        if len(tied) > 1
                        else "largest coverage gain"
                    )
                    partner_group_ids = tuple(
                        oid for oid in all_hash_ids if oid != best_b["id"]
                    )
                    ref = weapon_reference(
                        best_b["row"],
                        exact_roll_display_prefix(best_b["row"]),
                        distinguish_from=partner_group_ids,
                    )
                    n = len(a["matched"])
                    m = len(best_b["matched"])
                    keep_ref = weapon_keep_reference(
                        best_b["row"],
                        exact_roll_display_prefix(best_b["row"]),
                        distinguish_from=partner_group_ids,
                    )
                    expl = coverage_dominated(
                        n=n,
                        m=m,
                        keep_instead=keep_ref,
                    )
                    hashtag = (
                        f"#vc-review: coverage-dominated by; compare {ref}; "
                        f"curated matches {n} vs {m}; partner {partner_reason}"
                    )
                    note = append_tool_clause(a["row"]["Notes"], hashtag)
                    decisions.append(
                        Decision(
                            id=a["id"],
                            hash=str(a["row"]["Hash"]),
                            name=str(a["row"]["Name"]),
                            location=str(a["row"].get("Owner", "")),
                            guardian_class="",
                            action="review",
                            tag=str(a["row"]["Tag"]),
                            note=note,
                            kept_id=best_b["id"],
                            explanation=expl,
                        )
                    )
                    dominated_count += 1
            else:
                # Uncovered candidates: matched(A) is empty and matched(B) is non-empty.
                uncov_candidates = [
                    (b, len(b["matched"]))
                    for b in eligible_partners
                    if len(b["matched"]) > 0
                ]
                if uncov_candidates:
                    max_count = max(count for _, count in uncov_candidates)
                    tied = [b for b, count in uncov_candidates if count == max_count]
                    best_b = min(tied, key=lambda b: instance_id_order(b["id"]))
                    partner_reason = (
                        "deterministic id tie-break"
                        if len(tied) > 1
                        else "most curated matches"
                    )
                    partner_group_ids = tuple(
                        oid for oid in all_hash_ids if oid != best_b["id"]
                    )
                    ref = weapon_reference(
                        best_b["row"],
                        exact_roll_display_prefix(best_b["row"]),
                        distinguish_from=partner_group_ids,
                    )
                    m = len(best_b["matched"])
                    keep_ref = weapon_keep_reference(
                        best_b["row"],
                        exact_roll_display_prefix(best_b["row"]),
                        distinguish_from=partner_group_ids,
                    )
                    expl = coverage_uncovered(
                        m=m,
                        keep_instead=keep_ref,
                    )
                    hashtag = (
                        f"#vc-review: coverage-uncovered vs; compare {ref}; "
                        f"curated matches 0 vs {m}; partner {partner_reason}"
                    )
                    note = append_tool_clause(a["row"]["Notes"], hashtag)
                    decisions.append(
                        Decision(
                            id=a["id"],
                            hash=str(a["row"]["Hash"]),
                            name=str(a["row"]["Name"]),
                            location=str(a["row"].get("Owner", "")),
                            guardian_class="",
                            action="review",
                            tag=str(a["row"]["Tag"]),
                            note=note,
                            kept_id=best_b["id"],
                            explanation=expl,
                        )
                    )
                    uncovered_count += 1

    ordered_decisions = tuple(
        sorted(decisions, key=lambda decision: instance_id_order(decision.id))
    )
    summary = CoverageSummary(
        compared_instances=compared_instances,
        dominated=dominated_count,
        uncovered=uncovered_count,
        combination_counts=combination_counts,
        consensus_counts=consensus_counts,
    )
    return CoverageAnalysis(decisions=ordered_decisions, summary=summary)
