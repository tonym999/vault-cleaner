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
A tier-2 piece never dominates a tier-5. The Spirit signature remains part
of the existing identity boundary for every row. Exotic class items
additionally require exactly two visible Spirit perks; an incomplete
class-item roll is unknown and compared with nothing.

Runs after the exact pass on the pieces it left undecided: a dominator that
was junked as an exact dupe would be false advice ("a better copy exists" —
except it's leaving too), and its identical survivor covers every pair the
loser was part of. Similarity is not transitive, so notes are pairwise
(best partner per piece), never clusters; each piece gets at most one note.
Hard-protected pieces receive no note but still serve as dominator/partner.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

import pandas as pd

from vault_cleaner.duplicate_reference import (
    armor_reference,
    format_tuning_comparison,
    safe_fragment,
    tuning_mod_slot,
)
from vault_cleaner.note_history import append_tool_clause
from vault_cleaner.parse import ARMOR_STATS
from vault_cleaner.rules import rails
from vault_cleaner.rules.armor_dupes import (
    spirit_signature,
    unknown_spirit_roll,
)
from vault_cleaner.rules.dupes import Decision
from vault_cleaner.rules.id_order import instance_id_order


def _similar_detail(row: pd.Series, partner: pd.Series, mx: int, sm: int) -> str:
    if mx == 0:
        return "identical stats"
    return f"max stat delta {mx}, total {sm}"


@dataclass(frozen=True)
class ArmorSameStatMember:
    """One member of a review-only same-stat variation group."""

    id: str
    location: str
    protection_level: str | None
    protection_reason: str
    equipped: bool
    in_loadout: bool
    locked: bool
    masterwork_tier: int
    power: int
    tuning_stat: str
    tuning_mod_slot: str
    seasonal_mod: str
    holofoil: str
    proposal_action: str | None
    proposal_reason: str | None
    selected_partner_id: str | None


@dataclass(frozen=True)
class ArmorSameStatGroup:
    """A same-stat group emitted only when mutable variation is present."""

    group_kind: str
    group_id: str
    hash: str
    name: str
    type: str
    guardian_class: str
    item_archetype: str
    tier: int
    stats: Mapping[str, int]
    spirit_signature: tuple[str, ...]
    members: tuple[ArmorSameStatMember, ...]


@dataclass(frozen=True)
class ArmorCloseAnalysis:
    """One close pass result: decisions and its authoritative projection."""

    decisions: tuple[Decision, ...]
    same_stat_groups: tuple[ArmorSameStatGroup, ...]


@dataclass(frozen=True)
class _CloseDecisionResult:
    decisions: tuple[Decision, ...]
    reasons: Mapping[str, str]


def _close_decisions(armor: pd.DataFrame, cfg: dict) -> _CloseDecisionResult:
    caps = cfg["armor"]["close_dupes"]
    stat_cap, total_cap = caps["max_stat_delta"], caps["max_total_delta"]
    clp = cfg["rails"]["crafted_level_protect"]

    if armor.empty:
        return _CloseDecisionResult((), {})
    known = armor[~armor.apply(unknown_spirit_roll, axis=1)]
    known = known.assign(_spirits=known.apply(spirit_signature, axis=1))

    decisions: list[Decision] = []
    reasons: dict[str, str] = {}
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
            dom_candidates = []
            sim_candidates = []
            for oid, ostats, other in rows:
                if oid == rid:
                    continue
                delta = [o - s for o, s in zip(ostats, rstats)]
                if all(d >= 0 for d in delta) and any(d > 0 for d in delta):
                    # Largest surplus wins; lowest opaque id breaks ties.
                    dom_candidates.append((oid, sum(delta)))
                    surplus = sum(delta)
                    if (
                        best_dom is None
                        or surplus > best_dom[0]
                        or (
                            surplus == best_dom[0]
                            and instance_id_order(oid)
                            < instance_id_order(best_dom[1])
                        )
                    ):
                        best_dom = (surplus, oid, surplus, other)
                elif all(d <= 0 for d in delta) and any(d < 0 for d in delta):
                    continue  # this piece dominates the other: no advice here
                else:
                    mx, sm = max(abs(d) for d in delta), sum(abs(d) for d in delta)
                    if mx <= stat_cap and sm <= total_cap:
                        sim_candidates.append((oid, mx, sm))
                        key = (mx, sm)
                        if (
                            best_sim is None
                            or key < best_sim[0]
                            or (
                                key == best_sim[0]
                                and instance_id_order(oid)
                                < instance_id_order(best_sim[1])
                            )
                        ):
                            best_sim = (key, oid, other, mx, sm)
            if best_dom is not None:
                _, oid, surplus, other = best_dom
                # The existing key is (largest surplus, lowest id).  Explain
                # its first decisive dimension without rerunning selection.
                same_surplus = any(
                    candidate_id != oid and candidate_surplus == surplus
                    for candidate_id, candidate_surplus in dom_candidates
                )
                partner_reason = (
                    "deterministic id tie-break"
                    if same_surplus
                    else "largest stat surplus"
                )
                partner_group_ids = tuple(sorted(
                    (candidate_id for candidate_id, _, _ in rows if candidate_id != oid),
                    key=instance_id_order,
                ))
                reference = armor_reference(
                    other,
                    other.get("_spirits", ()),
                    distinguish_from=partner_group_ids,
                )
                tuning_comparison = format_tuning_comparison(
                    row["Tuning Stat"], other["Tuning Stat"], selected_label="Partner"
                )
                hashtag = (
                    f"#vc-review: armor-dominated by; compare {reference}; "
                    f"+{surplus} total; partner {partner_reason}; "
                    f"{tuning_comparison}"
                )
                partner_id = oid
            elif best_sim is not None:
                _, oid, other, mx, sm = best_sim
                detail = safe_fragment(_similar_detail(row, other, mx, sm), limit=96)
                partner_reason = (
                    "deterministic id tie-break"
                    if any(
                        candidate_id != oid
                        and candidate_mx == mx
                        and candidate_sm == sm
                        for candidate_id, candidate_mx, candidate_sm in sim_candidates
                    )
                    else "closest stat distance"
                )
                partner_group_ids = tuple(sorted(
                    (candidate_id for candidate_id, _, _ in rows if candidate_id != oid),
                    key=instance_id_order,
                ))
                reference = armor_reference(
                    other,
                    other.get("_spirits", ()),
                    distinguish_from=partner_group_ids,
                )
                tuning_comparison = format_tuning_comparison(
                    row["Tuning Stat"], other["Tuning Stat"], selected_label="Partner"
                )
                hashtag = (
                    f"#vc-review: armor-similar to; compare {reference}; "
                    f"{detail}; partner {partner_reason}; "
                    f"{tuning_comparison}"
                )
                partner_id = oid
            else:
                continue
            decisions.append(
                Decision(
                    id=rid, hash=row["Hash"], name=row["Name"],
                    location=row.get("Owner", ""),
                    guardian_class=row.get("Equippable", ""),
                    action="review", tag=row["Tag"],
                    note=append_tool_clause(row["Notes"], hashtag),
                    kept_id=partner_id,
                )
            )
            reasons[str(rid)] = (
                "armor-dominated by" if best_dom is not None else "armor-similar to"
            )
    # Decision sequence is part of the report contract.  Group iteration and
    # row iteration above intentionally preserve the close semantics and
    # partner choices, but the emitted sequence follows the shared opaque-ID
    # order so reversing an export cannot reorder the report.
    ordered_decisions = tuple(
        sorted(decisions, key=lambda decision: instance_id_order(decision.id))
    )
    return _CloseDecisionResult(ordered_decisions, reasons)


def _same_stat_key(row: pd.Series) -> tuple | None:
    if unknown_spirit_roll(row):
        return None
    stats = tuple(rails.to_int(row[c]) for c in ARMOR_STATS.values())
    # Match _close_decisions' raw Tier identity.  The projection converts it
    # back to an integer only for the existing display field.
    return (str(row["Hash"]), str(row["Tier"]), stats, spirit_signature(row))


def _same_stat_groups(
    armor: pd.DataFrame,
    decisions: tuple[Decision, ...],
    decision_reasons: Mapping[str, str],
    crafted_level_protect: int,
) -> tuple[ArmorSameStatGroup, ...]:
    grouped: dict[tuple, list[pd.Series]] = {}
    for _, row in armor.iterrows():
        key = _same_stat_key(row)
        if key is not None:
            grouped.setdefault(key, []).append(row)

    decision_by_id = {str(decision.id): decision for decision in decisions}
    groups: list[ArmorSameStatGroup] = []
    for key, rows in grouped.items():
        if len(rows) < 2:
            continue
        if not any(
            len({str(row[column]) for row in rows}) > 1
            for column in ("Tuning Stat", "Seasonal Mod", "Holofoil")
        ):
            continue
        rows = sorted(rows, key=lambda row: instance_id_order(row["Id"]))
        group_id = str(rows[0]["Id"])
        members = []
        for row in rows:
            decision = decision_by_id.get(str(row["Id"]))
            level, reason = rails.protection(row, crafted_level_protect)
            members.append(
                ArmorSameStatMember(
                    id=str(row["Id"]),
                    location=str(row.get("Owner", "")),
                    protection_level=level,
                    protection_reason=str(reason),
                    equipped=rails.is_true(row.get("Equipped", "")),
                    in_loadout=bool(str(row.get("Loadouts", "")).strip()),
                    locked=rails.is_true(row.get("Locked", "")),
                    masterwork_tier=rails.to_int(row.get("Masterwork Tier", "")),
                    power=rails.to_int(row.get("Power", "")),
                    tuning_stat=str(row.get("Tuning Stat", "")),
                    tuning_mod_slot=tuning_mod_slot(row.get("Tuning Stat", "")),
                    seasonal_mod=str(row.get("Seasonal Mod", "")),
                    holofoil=str(row.get("Holofoil", "")),
                    proposal_action=decision.action if decision else None,
                    proposal_reason=(
                        decision_reasons.get(str(decision.id))
                        if decision else None
                    ),
                    selected_partner_id=str(decision.kept_id) if decision and decision.kept_id else None,
                )
            )
        group_hash, tier_raw, stats, spirits = key
        groups.append(
            ArmorSameStatGroup(
                group_kind="same_stat",
                group_id=group_id,
                hash=group_hash,
                name=str(rows[0]["Name"]),
                type=str(rows[0]["Type"]),
                guardian_class=str(rows[0].get("Equippable", "")),
                item_archetype=str(rows[0].get("Archetype", "")),
                tier=rails.to_int(tier_raw),
                stats=MappingProxyType(dict(zip(ARMOR_STATS, stats))),
                spirit_signature=spirits,
                members=tuple(members),
            )
        )
    return tuple(
        sorted(
            groups,
            key=lambda group: (
                instance_id_order(group.group_id),
                group.hash,
                group.tier,
            ),
        )
    )


def analyse(
    armor: pd.DataFrame,
    cfg: dict,
    *,
    group_frame: pd.DataFrame | None = None,
) -> ArmorCloseAnalysis:
    """Run close decisions and project same-stat groups from the same pass.

    Decisions always come from ``armor``. ``group_frame`` supplies the wider
    comparison frame for the review-only projection, so a projected member
    may be a row that an earlier pass already decided; such a member carries
    no close proposal metadata.
    """
    decision_result = _close_decisions(armor, cfg)
    source = armor if group_frame is None else group_frame
    groups = _same_stat_groups(
        source,
        decision_result.decisions,
        decision_result.reasons,
        cfg["rails"]["crafted_level_protect"],
    )
    return ArmorCloseAnalysis(decision_result.decisions, groups)


def run(armor: pd.DataFrame, cfg: dict) -> list[Decision]:
    """Compatibility wrapper returning only the existing decisions."""
    return list(analyse(armor, cfg).decisions)
