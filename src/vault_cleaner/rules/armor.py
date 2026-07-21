"""Armor scoring pass (PLAN.md rule 4).

Each legendary piece is scored against every configured archetype and takes
its best score (plus a set bonus when a favored set perk is present). Scores
are normalized to the Total (Base) scale — a weighted archetype score equals
what Total (Base) would read if the piece's stats matched the archetype's
priorities perfectly — so one score floor works for every archetype.

Kept: the top-N pieces per slot per class, and anything at/above the floor.
Junked (with reason): pieces that are BOTH outside the top-N and below the
floor. Rails apply as everywhere: hard-protected pieces are untouched,
soft-protected (locked/exotic) get #vc-review instead of a junk tag —
though exotics never reach scoring at all (legendaries only).

Last-of-kind guard (#30): scoring never junks the vault's last kept copy of
a (Hash, Archetype) combination — Hash is class+slot+set (#16) and the
archetype fixes the 30/25 stat spike, i.e. which build the piece serves.
When every remaining copy of a combo is junk-bound, the best-scoring one is
demoted to review instead. Measured before designing: the dupe passes
already remove true duplicates, so 115 of 175 real-vault junk rows were the
last of their combo — set/build options were being foreclosed with no dupe
reasoning. Pieces kept by earlier passes count via `kept_elsewhere`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import pandas as pd

from vault_cleaner.parse import ARMOR_STATS
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import Decision

N_STATS = len(ARMOR_STATS)


@dataclass
class ArmorResult:
    decisions: list[Decision] = field(default_factory=list)
    scored: int = 0  # legendaries that went through scoring


def base_stats(row: pd.Series) -> dict[str, int]:
    return {name: rails.to_int(row[col]) for name, col in ARMOR_STATS.items()}


def score_archetype(stats: dict[str, int], archetype: dict) -> float:
    """Score on the Total (Base) scale. Two archetype forms:
    weights = {stat: w, ...} → N_STATS × weighted mean;
    top_stats = k → N_STATS × mean of the k highest stats (spike profile)."""
    if "top_stats" in archetype:
        k = int(archetype["top_stats"])
        top = sorted(stats.values(), reverse=True)[:k]
        return N_STATS * sum(top) / k if top else 0.0
    weights = archetype["weights"]
    total_w = sum(weights.values())
    if not total_w:
        return 0.0
    return N_STATS * sum(weights.get(s, 0) * v for s, v in stats.items()) / total_w


def best_score(stats: dict[str, int], archetypes: dict[str, dict]) -> tuple[float, str]:
    scored = [(score_archetype(stats, a), name) for name, a in archetypes.items()]
    return max(scored) if scored else (0.0, "none")


def has_favored_set_perk(row: pd.Series, favored: list[str]) -> bool:
    if not favored:
        return False
    # Strip to mirror the export-side normalization below — otherwise a
    # padded config name silently never matches
    wanted = {f.strip().casefold() for f in favored}
    for col in row.index:
        if not col.startswith("Perks "):
            continue
        for name in str(row[col]).split(","):
            if name.strip().removesuffix("*").strip().casefold() in wanted:
                return True
    return False


def _combo(row: pd.Series) -> tuple[str, str]:
    return (row["Hash"], row["Archetype"])


def run(
    armor: pd.DataFrame,
    cfg: dict,
    kept_elsewhere: frozenset[tuple[str, str]] = frozenset(),
) -> ArmorResult:
    """`kept_elsewhere` names (Hash, Archetype) combos that already have a
    surviving copy outside this frame (e.g. review-noted by a dupe pass)."""
    acfg = cfg["armor"]
    archetypes = acfg["archetypes"]
    result = ArmorResult()

    legendaries = armor[armor["Rarity"] == "Legendary"]
    result.scored = len(legendaries)

    # Phase 1: score every class+slot group; everything that isn't junk-bound
    # (kept, hard-protected, or soft-review) counts as a combo survivor.
    survivors: Counter = Counter(dict.fromkeys(kept_elsewhere, 1))
    junk_bound: list[tuple[float, pd.Series, str]] = []
    soft_reviews: list[tuple[pd.Series, str, str]] = []

    for (_, _), group in legendaries.groupby(["Equippable", "Type"], sort=False):
        scored_rows = []
        for _, row in group.iterrows():
            score, archetype = best_score(base_stats(row), archetypes)
            if has_favored_set_perk(row, acfg["favored_set_perks"]):
                score += acfg["set_bonus"]
            scored_rows.append((score, archetype, row))
        scored_rows.sort(key=lambda t: t[0], reverse=True)

        for rank, (score, archetype, row) in enumerate(scored_rows, start=1):
            if rank <= acfg["top_n_per_slot"] or score >= acfg["score_floor"]:
                survivors[_combo(row)] += 1
                continue
            level, reason = rails.protection(row, cfg["rails"]["crafted_level_protect"])
            if level == rails.HARD:
                survivors[_combo(row)] += 1
                continue
            detail = (
                f"armor-score {score:.1f} < floor {acfg['score_floor']} "
                f"(best: {archetype}, rank {rank}/{len(scored_rows)} "
                f"{row['Equippable'].lower()} {row['Type'].lower()})"
            )
            if level == rails.SOFT:
                survivors[_combo(row)] += 1
                soft_reviews.append((row, detail, reason))
            else:
                junk_bound.append((score, row, detail))

    # Phase 2: junk, except the best-scoring copy of a combo that would
    # otherwise vanish — that one is demoted to review (id breaks score
    # ties so CSV order never decides who is spared).
    junk_bound.sort(key=lambda t: (-t[0], int(t[1]["Id"])))
    for score, row, detail in junk_bound:
        if survivors[_combo(row)] == 0:
            survivors[_combo(row)] += 1
            label = row["Archetype"].lower() or "no archetype"
            action, tag = "review", row["Tag"]
            hashtag = f"#vc-review: armor-last-archetype ({label}), {detail}"
        else:
            action, tag = "junk", "junk"
            hashtag = f"#vc-junk: {detail}"
        result.decisions.append(
            Decision(
                id=row["Id"], hash=row["Hash"], name=row["Name"],
                owner=row.get("Owner", ""), action=action, tag=tag,
                note=f"{row['Notes']} {hashtag}".strip(), kept_id="",
            )
        )
    for row, detail, reason in soft_reviews:
        result.decisions.append(
            Decision(
                id=row["Id"], hash=row["Hash"], name=row["Name"],
                owner=row.get("Owner", ""), action="review", tag=row["Tag"],
                note=f"{row['Notes']} #vc-review: {detail} ({reason})".strip(), kept_id="",
            )
        )
    return result
