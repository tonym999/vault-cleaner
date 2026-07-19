"""Ghost shell cleanup pass (#8).

Policy (owner decision, PR #15): ghosts carry no quality signal — mods move
freely between shells, DIM's Energy Capacity / Masterwork Tier columns are
empty in current exports (retired system), and dismantled shells can be
reacquired from Collections. So there is no "best" to rank, and this pass
went through a ranking design before landing here — see WORKLOG 2026-07-19.
A shell is kept only for explicit reasons:

- tagged favorite/keep/archive or equipped (as everywhere),
- locked — for ghosts the lock IS the keep signal, so no `#vc-review`,
- referenced by a saved DIM loadout (`Loadouts` column non-empty).

Everything else — including unlocked Exotic-rarity shells; rarity is
cosmetic for ghosts — is junked as `#vc-junk: ghost-unprotected-surplus`.
Dry-run, DIM import review, and the in-game dismantle remain the gates.
"""

from __future__ import annotations

import pandas as pd

from vault_cleaner.rules import rails
from vault_cleaner.rules.dupes import Decision


def protection_reason(row: pd.Series) -> str | None:
    tag = row.get("Tag", "")
    if tag in rails.HARD_PROTECT_TAGS:
        return f"dim-tag:{tag}"
    if rails.is_true(row.get("Equipped", "")):
        return "equipped"
    if rails.is_true(row.get("Locked", "")):
        return "locked"
    if str(row.get("Loadouts", "")).strip():
        return "loadout"
    return None


def run(ghosts: pd.DataFrame) -> list[Decision]:
    decisions: list[Decision] = []
    for _, row in ghosts.iterrows():
        if protection_reason(row) is not None:
            continue
        hashtag = "#vc-junk: ghost-unprotected-surplus"
        decisions.append(
            Decision(
                id=row["Id"], hash=row["Hash"], name=row["Name"],
                owner=row.get("Owner", ""), action="junk", tag="junk",
                note=f"{row['Notes']} {hashtag}".strip(), kept_id="",
            )
        )
    return decisions
