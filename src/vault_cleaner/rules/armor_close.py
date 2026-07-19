"""Armor close-dupe pass (#18): dominated + similar, review-only.

"Close" is subjective, so this pass never tags junk — it writes `#vc-review`
notes and the human decides in DIM. Two categories:

- dominated: a compatible piece is >= in all six base stats and strictly >
  in at least one. Objective, but structurally near-extinct on current
  exports: every tier-5 piece totals exactly 75 base, and domination
  requires unequal totals (measured, #16). Kept because it's correct and
  cheap, and legacy/mixed-tier exports can still produce it.
- similar: stat vectors within configured limits (max per-stat delta, max
  sum of absolute deltas). On the real vault this is bimodal: pairs are
  either identical (usually differing only in Tuning Stat) or a whole
  archetype template apart, so any sane caps select the same pairs.

Compatibility: same Hash + same Tier + same Spirit signature. Measured
(#16): every vault legendary belongs to a manifest set and every set has
exactly one item hash per class x slot, so class+slot+tier+set-signature
collapses to Hash + Tier — which also covers the "exotics compare within
the same Hash only" rule and structurally excludes cross-set comparison.
A tier-2 piece never dominates a tier-5. The Spirit signature (empty for
everything but exotic class items) is the same identity rule: two
Stoicism with different Spirit combos are functionally different pieces,
and one with no visible spirits is an unknown roll — compared with
nothing.

Runs after the exact pass on the pieces it left undecided: a dominator that
was junked as an exact dupe would be false advice ("a better copy exists" —
except it's leaving too), and its identical survivor covers every pair the
loser was part of. Similarity is not transitive, so notes are pairwise
(best partner per piece), never clusters; each piece gets at most one note.
Hard-protected pieces receive no note but still serve as dominator/partner.
"""

from __future__ import annotations

import pandas as pd

from vault_cleaner.parse import ARMOR_STATS
from vault_cleaner.rules import rails
from vault_cleaner.rules.armor_dupes import spirit_signature, unknown_spirit_roll
from vault_cleaner.rules.dupes import Decision


def _similar_detail(row: pd.Series, partner: pd.Series, mx: int, sm: int) -> str:
    if mx == 0:
        ours, theirs = row["Tuning Stat"], partner["Tuning Stat"]
        if ours != theirs:
            return f"identical stats, tuning {ours or 'none'} vs {theirs or 'none'}"
        return "identical stats"
    return f"max stat delta {mx}, total {sm}"


def run(armor: pd.DataFrame, cfg: dict) -> list[Decision]:
    caps = cfg["armor"]["close_dupes"]
    stat_cap, total_cap = caps["max_stat_delta"], caps["max_total_delta"]
    clp = cfg["rails"]["crafted_level_protect"]

    if armor.empty:
        return []
    known = armor[~armor.apply(unknown_spirit_roll, axis=1)]
    known = known.assign(_spirits=known.apply(spirit_signature, axis=1))

    decisions: list[Decision] = []
    for _, group in known.groupby(["Hash", "Tier", "_spirits"], sort=False):
        if len(group) < 2:
            continue
        rows = [
            (r["Id"], tuple(rails.to_int(r[c]) for c in ARMOR_STATS.values()), r)
            for _, r in group.iterrows()
        ]
        for rid, rstats, row in rows:
            level, _ = rails.protection(row, clp)
            if level == rails.HARD:
                continue
            best_dom = best_sim = None
            for oid, ostats, other in rows:
                if oid == rid:
                    continue
                delta = [o - s for o, s in zip(ostats, rstats)]
                if all(d >= 0 for d in delta) and any(d > 0 for d in delta):
                    # Largest surplus wins; id breaks ties (never row order)
                    key = (sum(delta), -int(oid))
                    if best_dom is None or key > best_dom[0]:
                        best_dom = (key, oid, sum(delta))
                elif all(d <= 0 for d in delta) and any(d < 0 for d in delta):
                    continue  # this piece dominates the other: no advice here
                else:
                    mx, sm = max(abs(d) for d in delta), sum(abs(d) for d in delta)
                    if mx <= stat_cap and sm <= total_cap:
                        key = (mx, sm, int(oid))  # closest partner wins
                        if best_sim is None or key < best_sim[0]:
                            best_sim = (key, oid, other, mx, sm)
            if best_dom is not None:
                _, oid, surplus = best_dom
                hashtag = f"#vc-review: armor-dominated by {oid} (+{surplus} total)"
                partner_id = oid
            elif best_sim is not None:
                _, oid, other, mx, sm = best_sim
                hashtag = f"#vc-review: armor-similar to {oid} ({_similar_detail(row, other, mx, sm)})"
                partner_id = oid
            else:
                continue
            decisions.append(
                Decision(
                    id=rid, hash=row["Hash"], name=row["Name"],
                    owner=row.get("Owner", ""), action="review", tag=row["Tag"],
                    note=f"{row['Notes']} {hashtag}".strip(), kept_id=partner_id,
                )
            )
    return decisions
