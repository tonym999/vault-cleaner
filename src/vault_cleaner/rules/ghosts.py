"""Ghost shell cleanup pass (#8).

Ghosts fit none of the other passes, and the measured data reshaped the
original sketch: ghost mods are freely swappable between shells (the mod
carries the activity utility, not the shell), duplicate hashes don't occur,
and nearly every shell is Exotic *rarity* — which is cosmetic for ghosts.
So: rank all shells by Energy Capacity, then Masterwork Tier; keep the top
N (config `ghosts.keep_top_n`); junk the surplus with its rank as the
reason.

Rails, with one deliberate deviation: exotic rarity is NOT a soft rail here
(it would flag every shell and clean nothing). Tagged favorite/keep/archive
and equipped shells are hard-protected as usual; locked shells get
#vc-review instead of a junk tag.
"""

from __future__ import annotations

import pandas as pd

from vault_cleaner.parse import GHOST_RANK_COLUMNS
from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import Decision


def rank_key(row: pd.Series) -> tuple[int, ...]:
    # Current DIM exports leave these columns empty on every shell (retired
    # system), so keys often tie at (0, 0); ties fall back to export order.
    return tuple(rails.to_int(row.get(c)) for c in GHOST_RANK_COLUMNS)


def run(ghosts: pd.DataFrame, cfg: dict) -> list[Decision]:
    keep_top_n = cfg["ghosts"]["keep_top_n"]
    ranked = sorted(
        (row for _, row in ghosts.iterrows()),
        key=rank_key,
        reverse=True,
    )

    decisions: list[Decision] = []
    for rank, row in enumerate(ranked, start=1):
        if rank <= keep_top_n:
            continue
        level, _ = rails.protection(row, crafted_level_protect=0)
        if level == rails.HARD:
            continue
        key = rank_key(row)
        if any(key):
            detail = f"ghost-surplus (energy {key[0]}, rank {rank}/{len(ranked)})"
        else:
            # Don't fabricate a stat ranking the data doesn't contain
            detail = f"ghost-surplus (rank {rank}/{len(ranked)}, no energy/masterwork data)"
        # Checked directly: rails.protection reports "exotic" before "locked",
        # and for ghosts exotic is junk-eligible while locked still reviews.
        if rails.is_true(row.get("Locked", "")):
            action, tag = "review", row["Tag"]
            hashtag = f"#vc-review: {detail} (locked)"
        else:
            action, tag = "junk", "junk"
            hashtag = f"#vc-junk: {detail}"
        decisions.append(
            Decision(
                id=row["Id"], hash=row["Hash"], name=row["Name"],
                owner=row.get("Owner", ""), action=action, tag=tag,
                note=f"{row['Notes']} {hashtag}".strip(), kept_id="",
            )
        )
    return decisions
