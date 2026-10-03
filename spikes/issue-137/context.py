"""Template context for the Armor duplicates slice (spike for #137).

``build_context`` is a pure function from the schema-version-1 session
envelope (the ``dict`` that ``session_metadata`` returns) to the values the
templates print.  It ports *presentation* derivation only, from
``src/vault_cleaner/ui/review_ui.js``.  It never decides grouping, member
order, survivor choice or proposal eligibility: those are read from
``exact_duplicate_groups``, ``same_stat_groups``, ``disposition``,
``proposal_action``, the section's own ``decisions`` and the envelope's
``verdicts``.

The context depends on exactly four envelope fields: ``snapshot``,
``verdicts``, ``report_revision`` and ``verdict_revision`` (plus
``fingerprint``, which is a function of the snapshot).  It deliberately reads
neither ``state`` nor ``override_status``: both can change while the two
revisions stay equal (``POST /api/finalize`` does it), so anything rendered
from them could not be told apart by the revision pair.  The browser paints
those two from the envelope it has adopted instead.

``id`` and ``hash`` values are required to be ``str`` on the way in and are
only ever concatenated or compared; nothing here converts one to a number.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

NONE_UNKNOWN = "none/unknown"
DISPOSITION_LABELS = {
    "preferred_survivor": "Preferred survivor",
    "retained_protected": "Retained protected",
    "proposed_junk": "Proposed junk",
    "proposed_review": "Proposed review",
}
PROPOSAL_ACTIONS = ("junk", "review")
GROUP_KIND_FILTERS = ("all", "exact", "same_stat")
SECTION_COPY = {
    "exact": (
        "Exact duplicates",
        "Same archetype, same stats, same tuning — one copy survives",
    ),
    "same_stat": (
        "Same stats, different tuning",
        "Review only — the tool never picks your tuning for you",
    ),
}
SPIKE_ROLES = ((30, "Primary", "p"), (25, "Secondary", "s"), (20, "Tertiary", "t"))


class ContextError(ValueError):
    """The envelope does not have the shape the slice is allowed to render."""


def _text(value: object) -> str:
    """Mirror the browser's ``str()`` helper for display-only scalars."""
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _categorical(value: object) -> str:
    text = _text(value)
    return NONE_UNKNOWN if text == "" else text


def _opaque(value: object, where: str) -> str:
    """Accept an id or hash only as a string; never coerce it."""
    if not isinstance(value, str):
        raise ContextError(f"{where} must be a string")
    return value


def _yes_no(value: object) -> str:
    return "Yes" if value is True else "No"


def _unknown_or_text(value: object) -> str:
    return "unknown" if value is None else _text(value)


def _distinct(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _verdict_texts(persisted_veto: bool) -> dict[str, str]:
    """The three presentation strings a member can show, one per verdict."""
    if persisted_veto:
        suffix = "active persisted veto still suppresses this item"
        return {
            "": "Active persisted veto still suppresses this item",
            "approved": f"Approved this session · {suffix}",
            "vetoed": f"Vetoed this session · {suffix}",
        }
    return {"": "Unreviewed", "approved": "approved", "vetoed": "vetoed"}


def _proposals_by_id(section: Mapping[str, Any], where: str) -> dict[str, Mapping[str, Any]]:
    """Index the section's own proposal decisions; a lookup, not a decision."""
    proposals: dict[str, Mapping[str, Any]] = {}
    for index, decision in enumerate(section.get("decisions") or []):
        if not isinstance(decision, Mapping):
            continue
        if decision.get("action") not in PROPOSAL_ACTIONS:
            continue
        decision_id = _opaque(decision.get("id"), f"{where}.decisions[{index}].id")
        if decision_id in proposals:
            raise ContextError(f"duplicate proposal decision at {where}.decisions[{index}]")
        proposals[decision_id] = decision
    return proposals


def _stat_spike(stats: Mapping[str, Any], tier: object) -> dict[str, Any]:
    # The browser receives the snapshot through ``jsonify``, which sorts keys;
    # the in-process ``dict`` keeps insertion order.  Sort here so the stat
    # order is the one production shows (found by experiment E1).
    names = sorted(stats)
    values = [stats[name] for name in names]
    tier5 = (
        tier == 5
        and len(names) == 6
        and all(values.count(value) == 1 for value, _role, _css in SPIKE_ROLES)
        and values.count(0) == 3
    )
    if not tier5:
        return {
            "tier5": False,
            "tiles": [f"{_text(name)} {_text(stats[name])}" for name in names],
            "zero_summary": "",
        }
    rows = []
    for value, role, css in SPIKE_ROLES:
        name = next(name for name in names if stats[name] == value)
        rows.append(
            {"name": name, "value": _text(value), "role": role.lower(), "css": css}
        )
    zero_names = [name for name in names if stats[name] == 0]
    return {
        "tier5": True,
        "rows": rows,
        "zero_summary": " · ".join(zero_names) + " · 0 base",
    }


def _protection(member: Mapping[str, Any]) -> str:
    level = _text(member.get("protection_level"))
    if not level:
        return "—"
    reason = _text(member.get("protection_reason"))
    return f"{level} — {reason}" if reason else level


def _axes(kind: str, members: Sequence[Mapping[str, Any]]) -> tuple[list[dict], str]:
    """Split comparison axes into shown rows and the identical-axes sentence."""
    specs: list[dict[str, Any]] = []
    if kind == "same_stat":
        slots = [_categorical(member.get("tuning_mod_slot")) for member in members]
        raw_tuning = [_text(member.get("tuning_stat")) for member in members]
        informative = len(_distinct(raw_tuning)) > len(_distinct(slots))
        specs += [
            {"label": "Tuning Mod Slot", "always": True, "values": slots},
            {
                "label": "Seasonal Mod",
                "values": [_categorical(member.get("seasonal_mod")) for member in members],
            },
            {
                "label": "Holofoil",
                "values": [_categorical(member.get("holofoil")) for member in members],
            },
            {
                "label": "Tuning Stat",
                "skip_identical": True,
                "show": informative,
                "values": [value or NONE_UNKNOWN for value in raw_tuning],
            },
        ]
    specs += [
        {"label": "Protection", "values": [_protection(member) for member in members]},
        {"label": "In loadout", "values": [_yes_no(m.get("in_loadout")) for m in members]},
        {"label": "Equipped", "values": [_yes_no(m.get("equipped")) for m in members]},
        {"label": "Locked", "values": [_yes_no(m.get("locked")) for m in members]},
        {
            "label": "Masterwork Tier",
            "values": [_unknown_or_text(m.get("masterwork_tier")) for m in members],
        },
        {"label": "Power", "values": [_unknown_or_text(m.get("power")) for m in members]},
    ]
    rows: list[dict[str, Any]] = []
    identical: list[str] = []
    for spec in specs:
        distinct = _distinct(spec["values"])
        show = True if spec.get("always") else spec.get("show", len(distinct) > 1)
        if show:
            rows.append(
                {
                    "label": spec["label"],
                    "tuning": spec["label"] == "Tuning Mod Slot",
                    "cells": spec["values"],
                }
            )
        elif not spec.get("skip_identical") and len(distinct) <= 1:
            identical.append(f"{spec['label']} {distinct[0] if distinct else '—'}")
    line = "Identical across all pieces: " + " · ".join(identical) if identical else ""
    return rows, line


def _member(
    kind: str,
    source: Mapping[str, Any],
    index: int,
    group_hash: str,
    proposals: Mapping[str, Mapping[str, Any]],
    verdicts: Mapping[str, str],
    where: str,
) -> dict[str, Any]:
    member_id = _opaque(source.get("id"), f"{where}.id")
    proposal = proposals.get(member_id)
    current_action = ""
    current_reason = ""
    if proposal is not None:
        if _opaque(proposal.get("hash"), f"{where}.proposal_hash") != group_hash:
            raise ContextError(f"{where} has a proposal decision for another hash")
        current_action = _text(proposal.get("action"))
        current_reason = _text(proposal.get("reason"))
    proposal_action = _text(source.get("proposal_action"))
    kind_word = "same-stat" if kind == "same_stat" else "exact-duplicate"
    # Both wordings are rendered; the browser picks one from the adopted
    # envelope's ``override_status``.  The wording itself stays in Python.
    texts = _verdict_texts(False)
    persisted_texts = _verdict_texts(True)
    verdict = verdicts.get(member_id, "")

    if kind == "same_stat":
        if proposal_action and proposal_action not in PROPOSAL_ACTIONS:
            raise ContextError(f"{where}.proposal_action is unsupported")
        if proposal is not None and proposal_action and current_action != proposal_action:
            raise ContextError(f"{where} has inconsistent proposal action")
        can_verdict = current_action in PROPOSAL_ACTIONS
        label = (
            f"Existing Proposals action: {current_action}"
            if current_action
            else "Read-only comparison"
        )
        status = {"badge": "Read-only comparison", "before": [], "verdict": True, "after": []}
    else:
        disposition = _text(source.get("disposition"))
        if disposition not in DISPOSITION_LABELS:
            raise ContextError(f"{where} has an unsupported disposition")
        expected = {"proposed_junk": "junk", "proposed_review": "review"}.get(disposition, "")
        if proposal_action != expected or (
            proposal_action and current_action != proposal_action
        ):
            raise ContextError(f"{where} has inconsistent disposition/proposal action")
        can_verdict = bool(expected)
        label = DISPOSITION_LABELS[disposition]
        before = [f"Disposition: {label}"]
        if current_action:
            before.append(f"Also proposed {current_action} in Proposals")
        after = [f"Proposal reason: {current_reason}"] if current_action and current_reason else []
        status = {
            "badge": "Read-only",
            "before": before,
            "verdict": bool(current_action),
            "after": after,
        }

    return {
        "id": member_id,
        "dom_id": f"{kind}:{member_id}",
        "number": f"Member {index + 1}",
        "location": _text(source.get("location")) or "location unknown",
        "label": label,
        "can_verdict": can_verdict,
        "shows_verdict": can_verdict or status["verdict"],
        "is_junk_candidate": (
            current_action == "junk" if kind == "same_stat" else proposal_action == "junk"
        ),
        "verdict": verdict,
        "texts": texts,
        "persisted_texts": persisted_texts,
        "current_texts": {key: f"Current verdict: {text}" for key, text in texts.items()},
        "persisted_current_texts": {
            key: f"Current verdict: {text}" for key, text in persisted_texts.items()
        },
        "names": {
            "approved": f"approve {kind_word} armor member id {member_id}",
            "vetoed": f"veto {kind_word} armor member id {member_id}",
            "": f"unset verdict for {kind_word} armor member id {member_id}",
        },
        # A member with verdict controls shows no read-only status block.
        "status": None if can_verdict else status,
    }


def _group(
    kind: str,
    source: Mapping[str, Any],
    proposals: Mapping[str, Mapping[str, Any]],
    verdicts: Mapping[str, str],
    where: str,
) -> dict[str, Any]:
    if not isinstance(source, Mapping):
        raise ContextError(f"{where} must be an object")
    if source.get("group_kind") != kind:
        raise ContextError(f"{where}.group_kind must be {kind}")
    group_id = _opaque(source.get("group_id"), f"{where}.group_id")
    group_hash = _opaque(source.get("hash"), f"{where}.hash")
    raw_members = source.get("members")
    minimum = 2 if kind == "same_stat" else 1
    if not isinstance(raw_members, list) or len(raw_members) < minimum:
        raise ContextError(f"{where}.members is too short")
    if kind == "exact_duplicate":
        _opaque(source.get("preferred_survivor_id"), f"{where}.preferred_survivor_id")
    members = [
        _member(
            kind, member, index, group_hash, proposals, verdicts,
            f"{where}.members[{index}]",
        )
        for index, member in enumerate(raw_members)
    ]
    if len({member["id"] for member in members}) != len(members):
        raise ContextError(f"{where} repeats a member id")

    count = len(members)
    stats = source.get("stats") if isinstance(source.get("stats"), Mapping) else {}
    rows, identical_line = _axes(kind, raw_members)
    extras: list[tuple[str, str]] = []
    spirit = source.get("spirit_signature")
    if isinstance(spirit, list) and spirit:
        extras.append(("Spirit signature", " · ".join(_text(value) for value in spirit)))
    if kind == "same_stat":
        tuning_values = _distinct(
            [_categorical(member.get("tuning_mod_slot")) for member in raw_members]
        )
        banner = "Base stats match but tuning differs, so this pass selects no survivor."
        if any(member["can_verdict"] for member in members):
            banner += " Pieces below that already carry a proposal keep their verdict controls."
        kind_text = "Same stats · review only"
    else:
        tuning_values = [_categorical(source.get("tuning_mod_slot"))]
        suffix = (
            " — the only piece in this group."
            if count == 1
            else f" — identical across all {count} pieces, and part of why they are one group."
        )
        banner = tuning_values[0] + suffix
        kind_text = "Exact"
        seasonal = _text(source.get("seasonal_mod"))
        holofoil = _text(source.get("holofoil"))
        if seasonal:
            extras.append(("Seasonal Mod", seasonal))
        if holofoil and holofoil.lower() != "false":
            extras.append(("Holofoil", holofoil))

    tier = source.get("tier")
    return {
        "kind": kind,
        "filter_kind": "same_stat" if kind == "same_stat" else "exact",
        "dom_id": f"{kind}:{group_id}",
        "member_count": count,
        "name": _text(source.get("name")) or "(unnamed armor)",
        "archetype": f"Archetype: {_categorical(source.get('item_archetype'))}",
        "pieces": f"{count} piece" if count == 1 else f"{count} pieces",
        "type_text": f"Type/slot: {_categorical(source.get('type'))}",
        "class_text": f"Class: {_categorical(source.get('guardian_class'))}",
        "tier_text": f"Tier {_unknown_or_text(tier)}",
        "hash_text": f"Hash {group_hash}",
        "kind_text": kind_text,
        "spike": _stat_spike(stats, tier),
        "banner": {"warn": kind == "same_stat", "text": " " + banner},
        "identical_line": identical_line,
        "extras": extras,
        "has_junk": any(member["is_junk_candidate"] for member in members),
        "axes": rows,
        "members": members,
        "guardian_class": _categorical(source.get("guardian_class")),
        "tuning_values": tuning_values,
    }


def _projected_groups(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every group in the snapshot's own order: exact first, then same-stat."""
    snapshot = envelope.get("snapshot")
    if snapshot is None:
        return []
    verdicts = {
        _opaque(entry["id"], "verdicts[].id"): entry["verdict"]
        for entry in envelope.get("verdicts") or []
        if entry.get("verdict") in ("approved", "vetoed")
    }
    exact: list[dict[str, Any]] = []
    same_stat: list[dict[str, Any]] = []
    for index, section in enumerate(snapshot.get("sections") or []):
        armor = section.get("armor")
        if section.get("kind") != "armor" or not isinstance(armor, Mapping):
            continue
        where = f"sections[{index}]"
        proposals = _proposals_by_id(section, where)
        for key, kind, target in (
            ("exact_duplicate_groups", "exact_duplicate", exact),
            ("same_stat_groups", "same_stat", same_stat),
        ):
            for position, source in enumerate(armor.get(key) or []):
                target.append(
                    _group(
                        kind, source, proposals, verdicts,
                        f"{where}.armor.{key}[{position}]",
                    )
                )
    for groups in (exact, same_stat):
        ids = [group["dom_id"] for group in groups]
        if len(set(ids)) != len(ids):
            raise ContextError("a duplicate group id appears twice")
    return exact + same_stat


def _pieces(groups: Sequence[Mapping[str, Any]]) -> int:
    return sum(group["member_count"] for group in groups)


# [filters-b:start] server-side filtering (experiment E10, candidate b)
def _filtered(
    groups: Sequence[dict[str, Any]], kind: str, guardian_class: str
) -> list[dict[str, Any]]:
    return [
        group
        for group in groups
        if (kind == "all" or group["filter_kind"] == kind)
        and (not guardian_class or group["guardian_class"] == guardian_class)
    ]


def scope_text(
    groups: Sequence[Mapping[str, Any]],
    shown: Sequence[Mapping[str, Any]],
    kind: str,
    guardian_class: str,
) -> str:
    """Python port of ``duplicateScopeText`` for the two measured filters."""
    parts = []
    if kind == "exact":
        parts.append("exact duplicates")
    elif kind == "same_stat":
        parts.append("same-stat groups")
    if guardian_class:
        parts.append(f"class {guardian_class}")
    group_word = "group" if len(groups) == 1 else "groups"
    piece_word = "piece" if _pieces(groups) == 1 else "pieces"
    if not parts:
        return f"{len(groups)} {group_word} · {_pieces(groups)} {piece_word}"
    return (
        f"{len(shown)} of {len(groups)} {group_word} · "
        f"{_pieces(shown)} of {_pieces(groups)} {piece_word}"
        f" — filtered to {', '.join(parts)}"
    )


def _class_options(groups: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """Class facet options, counted over the selected kind's groups."""
    counts: dict[str, int] = {}
    for group in groups:
        counts[group["guardian_class"]] = counts.get(group["guardian_class"], 0) + 1
    return [
        {"value": value, "label": f"{value} ({count} {'group' if count == 1 else 'groups'})"}
        for value, count in sorted(counts.items(), key=lambda item: item[0].casefold())
    ]


def _reconciled_class(
    groups: Sequence[Mapping[str, Any]], kind: str, guardian_class: str
) -> tuple[list[dict[str, str]], str, str]:
    """Recount the options for the kind and drop a class the kind lacks."""
    universe = [group for group in groups if kind == "all" or group["filter_kind"] == kind]
    options = _class_options(universe)
    if guardian_class and guardian_class not in {option["value"] for option in options}:
        return options, "", guardian_class
    return options, guardian_class, ""
# [filters-b:end]


def build_context(
    envelope: Mapping[str, Any],
    *,
    kind: str = "all",
    guardian_class: str = "",
) -> dict[str, Any]:
    """Return the template context for one envelope.

    ``kind`` and ``guardian_class`` are the already-validated filter values
    of experiment E10's candidate (b); the defaults render every group.
    """
    if envelope.get("schema_version") != 1:
        raise ContextError("only the schema-version-1 envelope is supported")
    if kind not in GROUP_KIND_FILTERS:
        raise ContextError("unsupported group kind filter")
    groups = _projected_groups(envelope)
    class_options, guardian_class, dropped_class = _reconciled_class(
        groups, kind, guardian_class
    )
    shown = _filtered(groups, kind, guardian_class)
    sections = []
    for filter_kind in ("exact", "same_stat"):
        members = [group for group in shown if group["filter_kind"] == filter_kind]
        if members:
            heading, rule = SECTION_COPY[filter_kind]
            sections.append(
                {"kind": filter_kind, "heading": heading, "rule": rule, "groups": members}
            )
    fingerprint = envelope.get("fingerprint")
    return {
        "report_revision": str(envelope["report_revision"]),
        "verdict_revision": str(envelope["verdict_revision"]),
        "fingerprint": fingerprint if isinstance(fingerprint, str) else "",
        "total_groups": str(len(groups)),
        "total_pieces": str(_pieces(groups)),
        "scope_text": scope_text(groups, shown, kind, guardian_class),
        "class_options": class_options,
        "dropped_class": dropped_class,
        "sections": sections,
        "filtered_empty": bool(groups) and not shown,
    }
