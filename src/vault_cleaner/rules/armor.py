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
"""

from __future__ import annotations

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
    wanted = {f.casefold() for f in favored}
    for col in row.index:
        if not col.startswith("Perks "):
            continue
        for name in str(row[col]).split(","):
            if name.strip().removesuffix("*").strip().casefold() in wanted:
                return True
    return False


def run(armor: pd.DataFrame, cfg: dict) -> ArmorResult:
    acfg = cfg["armor"]
    archetypes = acfg["archetypes"]
    result = ArmorResult()

    legendaries = armor[armor["Rarity"] == "Legendary"]
    result.scored = len(legendaries)

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
                continue
            level, reason = rails.protection(row, cfg["rails"]["crafted_level_protect"])
            if level == rails.HARD:
                continue
            detail = (
                f"armor-score {score:.1f} < floor {acfg['score_floor']} "
                f"(best: {archetype}, rank {rank}/{len(scored_rows)} "
                f"{row['Equippable'].lower()} {row['Type'].lower()})"
            )
            if level == rails.SOFT:
                action, tag = "review", row["Tag"]
                hashtag = f"#vc-review: {detail} ({reason})"
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
    return result
