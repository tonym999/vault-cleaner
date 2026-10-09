"""What the slice must show, computed from the envelope alone (#206, S1).

This is the proofs' oracle.  It is written against the plan's *Required
information* list and reads only the server's schema-version-1 envelope.  It
shares no code with the frontend: if the TypeScript projection and this file
disagree, a proof fails.

``id`` and ``hash`` values are compared as the strings the server sent.
"""

from __future__ import annotations

from typing import Any

DISPOSITIONS = {
    "preferred_survivor": "Preferred survivor",
    "retained_protected": "Retained, protected",
    "proposed_junk": "Proposed junk",
    "proposed_review": "Proposed review",
}
PROPOSAL_DISPOSITIONS = {"proposed_junk": "junk", "proposed_review": "review"}
VERDICTS = {None: "Unreviewed", "approved": "Approved", "vetoed": "Vetoed"}
PRESSED = {None: "Unset", "approved": "Approve", "vetoed": "Veto"}
SPIKE = {30: "primary", 25: "secondary", 20: "tertiary"}

Cell = tuple[str, bool]  # (text, is it an absent value)


def _categorical(value: str) -> Cell:
    return ("none", True) if value == "" else (value, False)


def _tuning_slot(value: str) -> Cell:
    # The server's own sentinel for "no known slot" (duplicate_reference.py).
    return (value, True) if value == "none/unknown" else _categorical(value)


def _number(value: Any) -> Cell:
    return ("unknown", True) if value is None else (str(value), False)


def _yes_no(value: bool) -> Cell:
    return ("Yes" if value else "No", False)


def _protection(member: dict) -> Cell:
    level = member["protection_level"]
    if not level:
        return ("none", True)
    reason = member["protection_reason"]
    return (f"{level} — {reason}" if reason else level, False)


def _member_fields(kind: str, member: dict) -> dict[str, Cell]:
    fields: dict[str, Cell] = {}
    if kind == "same_stat":
        fields["tuning_mod_slot"] = _tuning_slot(member["tuning_mod_slot"])
        fields["tuning_stat"] = _categorical(member["tuning_stat"])
        fields["seasonal_mod"] = _categorical(member["seasonal_mod"])
        fields["holofoil"] = _categorical(member["holofoil"])
    fields["protection"] = _protection(member)
    fields["in_loadout"] = _yes_no(member["in_loadout"])
    fields["equipped"] = _yes_no(member["equipped"])
    fields["locked"] = _yes_no(member["locked"])
    fields["masterwork_tier"] = _number(member["masterwork_tier"])
    fields["power"] = _number(member["power"])
    return fields


def _stats(group: dict) -> dict[str, tuple[str, str]]:
    stats = group["stats"]
    values = list(stats.values())
    spike = (
        group["tier"] == 5
        and len(stats) == 6
        and all(values.count(value) == 1 for value in SPIKE)
        and values.count(0) == 3
    )
    return {
        name: (str(value), SPIKE.get(value, "") if spike else "")
        for name, value in stats.items()
    }


def expected_groups(envelope: dict) -> list[dict]:
    """Every group, exact first then same-stat, each in the server's order."""
    snapshot = envelope["snapshot"]
    if snapshot is None:
        return []
    verdicts = {entry["id"]: entry["verdict"] for entry in envelope["verdicts"]}
    persisted = {
        entry["id"] for entry in envelope["override_status"] if entry["status"] == "active"
    }
    ordered: dict[str, list[dict]] = {"exact": [], "same_stat": []}
    for section in snapshot["sections"]:
        armor = section.get("armor")
        if armor is None:
            continue
        proposals = {decision["id"]: decision for decision in section["decisions"]}
        for kind, key in (("exact", "exact_duplicate_groups"), ("same_stat", "same_stat_groups")):
            for group in armor[key]:
                ordered[kind].append(_group(kind, group, proposals, verdicts, persisted))
    return ordered["exact"] + ordered["same_stat"]


def _group(kind: str, group: dict, proposals: dict, verdicts: dict, persisted: set) -> dict:
    members = group["members"]
    per_member = [_member_fields(kind, member) for member in members]
    differing = [
        name for name in per_member[0]
        if len({fields[name][0] for fields in per_member}) > 1
    ]
    shared = {name: cell for name, cell in per_member[0].items() if name not in differing}
    if kind == "exact":
        shared["tuning_mod_slot"] = _tuning_slot(group["tuning_mod_slot"])
        if group["seasonal_mod"]:
            shared["seasonal_mod"] = (group["seasonal_mod"], False)
        if group["holofoil"] and group["holofoil"].lower() != "false":
            shared["holofoil"] = (group["holofoil"], False)
    if group["spirit_signature"]:
        shared["spirit_signature"] = (" · ".join(group["spirit_signature"]), False)
    count = len(members)
    rows = []
    for member, fields in zip(members, per_member, strict=True):
        proposal = proposals.get(member["id"])
        if kind == "exact":
            # An unknown disposition is shown as it arrived, never guessed.
            status = DISPOSITIONS.get(member["disposition"], member["disposition"])
            # Production's rule: disposition and proposal action agree, and the
            # section's proposal carries that action.
            controls = (
                proposal is not None
                and PROPOSAL_DISPOSITIONS.get(member["disposition"]) == proposal["action"]
                and member["proposal_action"] == proposal["action"]
            )
        else:
            status = f"Existing proposal: {proposal['action']}" if proposal else "Comparison only"
            controls = proposal is not None and proposal["action"] in ("junk", "review")
        verdict = verdicts.get(member["id"])
        rows.append({
            "id": member["id"],
            "location": (member["location"], False) if member["location"] else ("unknown", True),
            "status": status,
            "differing": {name: fields[name] for name in differing},
            "proposal": None if proposal is None else {
                "action": proposal["action"],
                "reason": _categorical(proposal["reason"]),
                "verdict": VERDICTS[verdict],
                "persisted_veto": member["id"] in persisted,
            },
            "controls": controls,
            "pressed": PRESSED[verdict],
        })
    return {
        "key": f"{kind}:{group['group_id']}",
        "kind": kind,
        "name": (group["name"], False) if group["name"] else ("Unnamed armor", True),
        "kind_text": "Exact duplicates" if kind == "exact" else "Same stats · review only",
        "piece_count": f"{count} piece" if count == 1 else f"{count} pieces",
        "facts": {
            "item_archetype": _categorical(group["item_archetype"]),
            "type": _categorical(group["type"]),
            "guardian_class": _categorical(group["guardian_class"]),
            "tier": _number(group["tier"]),
            "hash": (group["hash"], False),
        },
        "stats": _stats(group),
        "shared": shared,
        "differing": differing,
        "members": rows,
    }


def expected_scope(groups: list[dict]) -> str:
    pieces = sum(len(group["members"]) for group in groups)
    return (
        f"{len(groups)} {'group' if len(groups) == 1 else 'groups'} · "
        f"{pieces} {'piece' if pieces == 1 else 'pieces'}"
    )


def _cell(shown: dict | None, wanted: Cell, where: str, problems: list[str]) -> None:
    if shown is None:
        problems.append(f"{where}: not shown")
    elif (shown["text"], shown["unknown"]) != wanted:
        problems.append(f"{where}: shows {(shown['text'], shown['unknown'])!r}, server says {wanted!r}")
    elif not shown["visible"]:
        problems.append(f"{where}: present but not visible without interaction")


def compare(shown: dict, envelope: dict, *, frozen: bool = False) -> list[str]:
    """Every difference between the page and what the envelope requires."""
    problems: list[str] = []
    groups = expected_groups(envelope)
    if [group["key"] for group in shown["groups"]] != [group["key"] for group in groups]:
        problems.append(
            f"group order: page {[g['key'] for g in shown['groups']]}, "
            f"server {[g['key'] for g in groups]}"
        )
        return problems
    if shown["scope"] != expected_scope(groups):
        problems.append(f"scope: page {shown['scope']!r}, server {expected_scope(groups)!r}")
    for page_group, group in zip(shown["groups"], groups, strict=True):
        where = group["key"]
        fields = page_group["fields"]
        _cell(fields.get("name"), group["name"], f"{where} name", problems)
        _cell(fields.get("kind"), (group["kind_text"], False), f"{where} kind", problems)
        _cell(fields.get("piece_count"), (group["piece_count"], False), f"{where} pieces", problems)
        if (fields.get("review_only") is not None) != (group["kind"] == "same_stat"):
            problems.append(f"{where}: the review-only notice is on the wrong kind of group")
        for name, cell in group["facts"].items():
            _cell(fields.get(name), cell, f"{where} {name}", problems)
        shown_stats = {
            name: (stat["value"], stat["role"]) for name, stat in page_group["stats"].items()
        }
        if shown_stats != group["stats"]:
            problems.append(f"{where} stats: page {shown_stats}, server {group['stats']}")
        if not all(stat["visible"] for stat in page_group["stats"].values()):
            problems.append(f"{where} stats: not all visible")
        if set(page_group["shared"]) != set(group["shared"]):
            problems.append(
                f"{where} shared values: page {sorted(page_group['shared'])}, "
                f"server {sorted(group['shared'])}"
            )
        for name, cell in group["shared"].items():
            _cell(page_group["shared"].get(name), cell, f"{where} shared {name}", problems)
        if [m["id"] for m in page_group["members"]] != [m["id"] for m in group["members"]]:
            problems.append(f"{where}: member order differs")
            continue
        for page_member, member in zip(page_group["members"], group["members"], strict=True):
            at = f"{where} member {member['id']}"
            shown_fields = page_member["fields"]
            _cell(shown_fields.get("id"), (member["id"], False), f"{at} id", problems)
            _cell(shown_fields.get("location"), member["location"], f"{at} location", problems)
            _cell(shown_fields.get("status"), (member["status"], False), f"{at} status", problems)
            for name, cell in member["differing"].items():
                _cell(shown_fields.get(name), cell, f"{at} {name}", problems)
            proposal = member["proposal"]
            if proposal is None:
                for name in ("proposal_action", "proposal_reason", "verdict", "persisted_veto"):
                    if name in shown_fields:
                        problems.append(f"{at}: shows {name} but the server has no proposal for it")
            else:
                _cell(shown_fields.get("proposal_action"), (proposal["action"], False),
                      f"{at} proposed action", problems)
                _cell(shown_fields.get("proposal_reason"), proposal["reason"],
                      f"{at} proposal reason", problems)
                _cell(shown_fields.get("verdict"), (proposal["verdict"], False),
                      f"{at} verdict", problems)
                if ("persisted_veto" in shown_fields) != proposal["persisted_veto"]:
                    problems.append(f"{at}: persisted-veto notice shown="
                                    f"{'persisted_veto' in shown_fields}, server={proposal['persisted_veto']}")
            buttons = page_member["buttons"]
            if bool(buttons) != member["controls"]:
                problems.append(f"{at}: verdict controls shown={bool(buttons)}, "
                                f"server makes it a proposal member={member['controls']}")
            if buttons:
                pressed = [button["label"] for button in buttons if button["pressed"] == "true"]
                if pressed != [member["pressed"]]:
                    problems.append(f"{at}: pressed {pressed}, server verdict means [{member['pressed']!r}]")
                names = [button["name"] for button in buttons]
                wanted = [f"{label} item {member['id']}" for label in ("Approve", "Veto", "Unset")]
                if names != wanted:
                    problems.append(f"{at}: control names {names}")
                if any(button["disabled"] != frozen for button in buttons):
                    problems.append(f"{at}: controls disabled state is not {frozen}")
                if not all(button["visible"] for button in buttons):
                    problems.append(f"{at}: a verdict control is not visible")
    return problems
