from pathlib import Path

import pytest

from vault_cleaner.parse import SchemaError, load_armor
from vault_cleaner.report import reason_slug
from vault_cleaner.rules.armor_dupes import (
    analyse,
    fingerprint,
    run,
    spirit_signature,
)

FIXTURE = Path(__file__).parent / "fixtures" / "armor_dupes.csv"

# Static semantic capture from origin/main (190e8473), before the group
# projection refactor. Every Decision field and its parsed reason is included
# so the projection cannot silently alter the authoritative exact pass.
BASELINE_DECISIONS = (
    (
        "5002", "700", "Dupe Plate", "Vault", "Titan", "junk", "junk",
        (
            "old note #vc-junk: armor-exact-dupe; keep [id 5001; location Vault; "
            "MW5; power 450; tuning melee]; winner higher Masterwork Tier"
        ),
        "5001", ("junk", "armor-exact-dupe"),
    ),
    (
        "5012", "710", "Loadout Plate", "Vault", "Titan", "review", "",
        (
            "#vc-review: armor-exact-dupe (loadout); keep [id 5011; location Vault; "
            "MW0; power 0; tuning grenade]; winner hard protection"
        ),
        "5011", ("review", "armor-exact-dupe"),
    ),
    (
        "5022", "720", "Tie Plate", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exact-dupe-tie; keep [id 5021; location Vault; "
            "MW0; power 0; tuning class]; winner deterministic id tie-break"
        ),
        "5021", ("junk", "armor-exact-dupe-tie"),
    ),
    (
        "5032", "730", "Exotic Mark", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exotic-class-dupe; keep [id 5031; location Vault; "
            "MW1; power 0; spirits Contact + Assassin]; winner higher Masterwork Tier"
        ),
        "5031", ("junk", "armor-exotic-class-dupe"),
    ),
    (
        "5061", "770", "Equipped Plate", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exact-dupe; keep [id 5062; location Vault; "
            "MW0; power 0; tuning weapons]; winner hard protection"
        ),
        "5062", ("junk", "armor-exact-dupe"),
    ),
    (
        "5072", "780", "Power Plate", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exact-dupe; keep [id 5071; location Vault; "
            "MW3; power 460; tuning super]; winner higher Power"
        ),
        "5071", ("junk", "armor-exact-dupe"),
    ),
    (
        "5082", "790", "Loadout Beats MW", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exact-dupe; keep [id 5081; location Vault; "
            "MW0; power 400; tuning health]; winner loadout membership"
        ),
        "5081", ("junk", "armor-exact-dupe"),
    ),
    (
        "5092", "800", "Lock Beats MW", "Vault", "Titan", "junk", "junk",
        (
            "#vc-junk: armor-exact-dupe; keep [id 5091; location Vault; "
            "MW0; power 0; tuning melee]; winner lock"
        ),
        "5091", ("junk", "armor-exact-dupe"),
    ),
    (
        "5102", "810", "Locked Pair", "Vault", "Titan", "review", "",
        (
            "#vc-review: armor-exact-dupe (locked); keep [id 5101; location Vault; "
            "MW3; power 0; tuning class]; winner higher Masterwork Tier"
        ),
        "5101", ("review", "armor-exact-dupe"),
    ),
    (
        "5122", "830", "Plain Exotic", "Vault", "Titan", "review", "",
        (
            "#vc-review: armor-exact-dupe (exotic); keep [id 5121; location Vault; "
            "MW1; power 0]; winner higher Masterwork Tier"
        ),
        "5121", ("review", "armor-exact-dupe"),
    ),
)


def decisions(frame=None):
    return run(frame if frame is not None else load_armor(FIXTURE), crafted_level_protect=10)


def by_id(ds):
    return {d.id: d for d in ds}


def test_exact_decisions_match_origin_main_capture():
    actual = tuple(
        (
            decision.id,
            decision.hash,
            decision.name,
            decision.location,
            decision.guardian_class,
            decision.action,
            decision.tag,
            decision.note,
            decision.kept_id,
            reason_slug(decision.note),
        )
        for decision in decisions()
    )
    assert actual == BASELINE_DECISIONS


def test_higher_masterwork_survives_and_loser_junked_with_note_appended():
    d = by_id(decisions())
    assert "5001" not in d  # survivor: no output row
    assert d["5002"].action == "junk"
    assert d["5002"].tag == "junk"
    assert d["5002"].note == (
        "old note #vc-junk: armor-exact-dupe; keep [id 5001; location Vault; "
        "MW5; power 450; tuning melee]; winner higher Masterwork Tier"
    )
    assert "winner higher Masterwork Tier" in d["5002"].note


def test_legacy_owner_duplicate_reference_is_replaced_with_location():
    armor = load_armor(FIXTURE)
    armor.loc[armor["Id"] == "5002", "Notes"] = (
        "manual context #vc-junk: armor-exact-dupe; keep "
        "[id 5001; owner Old]; winner higher Masterwork Tier"
    )
    decision = by_id(decisions(armor))["5002"]
    assert decision.note.startswith("manual context #vc-junk: armor-exact-dupe;")
    assert decision.note.count("#vc-junk:") == 1
    assert "owner Old" not in decision.note
    assert "location Vault" in decision.note


def test_loadout_referenced_loser_reviews_never_junk():
    # DIM loadouts pin instance ids — junking a loadout member breaks the
    # loadout even when an identical twin survives
    d = by_id(decisions())
    assert "5011" not in d  # hard-protected survivor (tagged keep)
    assert d["5012"].action == "review"
    assert d["5012"].tag == ""  # existing tag preserved
    assert "#vc-review: armor-exact-dupe (loadout); keep [id 5011" in d["5012"].note
    assert "5013" not in d  # equipped copy loses the id tie-break but is hard: no row


def test_tie_survivor_is_lowest_id_not_row_order():
    # fixture lists 5022 before 5021: export order must not pick the survivor
    d = by_id(decisions())
    assert "5021" not in d
    assert d["5022"].action == "junk"
    assert "#vc-junk: armor-exact-dupe-tie; keep [id 5021" in d["5022"].note
    assert "winner deterministic id tie-break" in d["5022"].note


def test_reversing_the_csv_changes_nothing():
    forward = {(d.id, d.action, d.note) for d in decisions()}
    reversed_ = {(d.id, d.action, d.note) for d in decisions(load_armor(FIXTURE).iloc[::-1])}
    assert forward == reversed_


def test_complete_exotic_class_loser_junks_and_spirit_roll_splits_the_group():
    d = by_id(decisions())
    assert "5031" not in d  # best exotic copy survives
    assert d["5032"].action == "junk"
    assert "#vc-junk: armor-exotic-class-dupe; keep [id 5031" in d["5032"].note
    assert "5033" not in d  # different Spirit combo — a different roll


def test_same_name_different_hash_never_groups():
    d = by_id(decisions())
    assert "5041" not in d and "5042" not in d


def test_tuning_stat_is_roll_identity():
    # identical stats, different Tuning Stat: different rolls (measured, #16)
    d = by_id(decisions())
    assert "5051" not in d and "5052" not in d


def test_artifice_splits_the_group():
    d = by_id(decisions())
    assert "5053" not in d and "5054" not in d


def test_equipped_copy_survives_over_higher_masterwork():
    d = by_id(decisions())
    assert "5062" not in d  # equipped: hard protection tops the survivor order
    assert d["5061"].action == "junk"
    assert d["5061"].kept_id == "5062"


def test_power_breaks_masterwork_tie():
    d = by_id(decisions())
    assert "5071" not in d
    assert d["5072"].action == "junk"
    assert d["5072"].kept_id == "5071"
    assert "winner higher Power" in d["5072"].note


def test_loadout_membership_outranks_masterwork():
    d = by_id(decisions())
    assert "5081" not in d  # in a loadout, mw 0: still the survivor
    assert d["5082"].action == "junk"
    assert d["5082"].kept_id == "5081"
    assert "winner loadout membership" in d["5082"].note


def test_lock_outranks_masterwork_and_locked_loser_reviews():
    d = by_id(decisions())
    assert "5091" not in d  # locked, mw 0: survivor over mw 5
    assert d["5092"].action == "junk"
    assert d["5092"].kept_id == "5091"
    assert "winner lock" in d["5092"].note
    # all-locked group: loser is soft-protected, reviews with the lock named
    assert "5101" not in d
    assert d["5102"].action == "review"
    assert "#vc-review: armor-exact-dupe (locked); keep [id 5101" in d["5102"].note


def test_spiritless_exotic_class_items_never_group():
    # No visible Spirit perks means the roll is unknown — an unknown roll
    # can't be proven identical to anything, so no grouping, no advice
    d = by_id(decisions())
    assert "5111" not in d and "5112" not in d


def test_truncated_spirit_signatures_never_group():
    # A single visible Spirit (of a measured two) is incomplete identity:
    # two distinct rolls sharing their first Spirit must not merge
    d = by_id(decisions())
    assert "5131" not in d and "5132" not in d


def test_more_than_two_spirit_perks_is_unknown_and_never_groups():
    armor = load_armor(FIXTURE)
    armor.loc[armor["Id"] == "5031", "Perks 2"] = "Spirit of Alpha Lupi"
    result = analyse(armor, crafted_level_protect=10)
    assert "730" not in {group.hash for group in result.groups}
    assert "5031" not in {decision.id for decision in result.decisions}
    assert "5032" not in {decision.id for decision in result.decisions}


@pytest.mark.parametrize("state", ["hard", "loadout", "locked"])
def test_complete_exotic_class_loser_respects_narrow_protection_rails(state):
    armor = load_armor(FIXTURE)
    # An equipped survivor makes the state under test unambiguously a loser;
    # the complete Spirit pair remains the exact identity.
    armor.loc[armor["Id"] == "5031", "Equipped"] = "true"
    if state == "hard":
        armor.loc[armor["Id"] == "5032", "Equipped"] = "true"
    elif state == "loadout":
        armor.loc[armor["Id"] == "5032", "Loadouts"] = "PvE Build"
    else:
        armor.loc[armor["Id"] == "5032", "Locked"] = "true"

    result = analyse(armor, crafted_level_protect=10)
    decisions_by_id = {decision.id: decision for decision in result.decisions}
    group = next(group for group in result.groups if group.hash == "730")
    member_by_id = {member.id: member for member in group.members}
    if state == "hard":
        assert "5032" not in decisions_by_id
        assert member_by_id["5032"].disposition == "retained_protected"
        assert member_by_id["5032"].protection_level == "hard"
    else:
        assert decisions_by_id["5032"].action == "review"
        assert reason_slug(decisions_by_id["5032"].note) == (
            "review", "armor-exotic-class-dupe"
        )
        assert member_by_id["5032"].disposition == "proposed_review"
        assert member_by_id["5032"].protection_reason == state


def test_plain_exotics_without_spirits_still_group():
    # Non-class-item exotics legitimately have no Spirit perks; the guard
    # must not exempt them from normal dupe grouping
    d = by_id(decisions())
    assert "5121" not in d  # survivor
    assert d["5122"].action == "review"
    assert "#vc-review: armor-exact-dupe (exotic); keep [id 5121" in d["5122"].note


def test_fingerprint_ignores_mutable_state():
    df = load_armor(FIXTURE).set_index("Id", drop=False)
    a, b = df.loc["5001"], df.loc["5002"]  # differ in mw/power/notes only
    assert fingerprint(a) == fingerprint(b)


def test_spirit_signature_reads_only_spirit_perks():
    df = load_armor(FIXTURE).set_index("Id", drop=False)
    assert spirit_signature(df.loc["5031"]) == ("Spirit of Contact", "Spirit of the Assassin")
    assert spirit_signature(df.loc["5001"]) == ()


def test_non_class_spirit_looking_perks_remain_exact_identity():
    armor = load_armor(FIXTURE)
    mask = armor["Id"].isin(["5001", "5002"])
    armor.loc[armor["Id"] == "5001", "Perks 0"] = "Spirit of Future A"
    armor.loc[armor["Id"] == "5002", "Perks 0"] = "Spirit of Future B"

    result = analyse(armor.loc[mask], crafted_level_protect=10)

    assert spirit_signature(armor.loc[armor["Id"] == "5001"].iloc[0]) == (
        "Spirit of Future A",
    )
    assert result.decisions == ()
    assert result.groups == ()


@pytest.mark.parametrize("column", ["Tuning Stat", "Perks 0"])
def test_missing_fingerprint_column_fails_loudly(tmp_path, column):
    # A vanished fingerprint column must not silently merge dupe groups —
    # Perks 0 carries the Spirit roll identity for exotic class items
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index(column)
    stripped = [",".join(cells.split(",")[:idx] + cells.split(",")[idx + 1:]) for cells in lines]
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join(stripped) + "\n")
    with pytest.raises(SchemaError, match=column.replace(" ", r"\s")):
        load_armor(bad)


@pytest.mark.parametrize(("column", "value"), [("Masterwork Tier", "abc"), ("Power", "-5")])
def test_malformed_ranking_cell_fails_loudly(tmp_path, column, value):
    # to_int would coerce these to 0 and silently flip the dupe survivor
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index(column)
    row = lines[1].split(",")
    row[idx] = value
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join([lines[0], ",".join(row)] + lines[2:]) + "\n")
    with pytest.raises(SchemaError, match=f"malformed '{column}' value '{value}'"):
        load_armor(bad)


def test_empty_ranking_cells_stay_legitimate(tmp_path):
    # Empty means "unmasterworked", not corrupt — strict validation here was
    # the ghost-pass mistake (it rejected the real export)
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    row = lines[1].split(",")
    row[header.index("Masterwork Tier")] = ""
    row[header.index("Power")] = ""
    ok = tmp_path / "ok.csv"
    ok.write_text("\n".join([lines[0], ",".join(row)] + lines[2:]) + "\n")
    assert len(load_armor(ok)) == len(load_armor(FIXTURE))


def test_analysis_projects_complete_groups_and_decision_dispositions():
    result = analyse(load_armor(FIXTURE), crafted_level_protect=10)

    assert len(result.decisions) == 10
    assert len(result.groups) == 10
    group = next(group for group in result.groups if group.hash == "710")
    assert group.group_kind == "exact_duplicate"
    assert group.group_id == "5011"
    assert group.preferred_survivor_id == "5011"
    assert group.tier == 5
    assert group.stats == {
        "weapons": 5,
        "health": 20,
        "class": 10,
        "grenade": 5,
        "super": 5,
        "melee": 30,
    }
    assert group.tuning_mod_slot == "Grenade"
    assert [member.id for member in group.members] == ["5011", "5013", "5012"]
    dispositions = {member.id: member.disposition for member in group.members}
    assert dispositions == {
        "5011": "preferred_survivor",
        "5012": "proposed_review",
        "5013": "retained_protected",
    }
    retained = next(member for member in group.members if member.id == "5013")
    survivor = next(member for member in group.members if member.id == "5011")
    assert survivor.location == "Vault"
    assert survivor.protection_level == "hard"
    assert survivor.protection_reason == "dim-tag:keep"
    assert survivor.equipped is False
    assert survivor.in_loadout is False
    assert survivor.locked is False
    assert survivor.masterwork_tier == 0
    assert survivor.power == 0
    assert survivor.proposal_action is None
    assert survivor.proposal_reason is None
    assert retained.protection_level == "hard"
    assert retained.protection_reason == "equipped"
    assert retained.equipped is True
    assert retained.in_loadout is False
    assert retained.locked is False
    assert retained.masterwork_tier == 0
    assert retained.power == 0
    assert retained.proposal_action is None
    proposal = next(member for member in group.members if member.id == "5012")
    assert proposal.location == "Vault"
    assert proposal.protection_level is None
    assert proposal.protection_reason == ""
    assert proposal.equipped is False
    assert proposal.in_loadout is True
    assert proposal.locked is False
    assert proposal.masterwork_tier == 0
    assert proposal.power == 0
    assert proposal.proposal_action == "review"
    assert proposal.proposal_reason == "armor-exact-dupe"

    decisions_by_id = {decision.id: decision for decision in result.decisions}
    for member in group.members:
        if member.disposition.startswith("proposed_"):
            decision = decisions_by_id[member.id]
            assert member.proposal_action == decision.action
        else:
            assert member.id not in decisions_by_id


def test_group_member_order_prioritizes_survivor_before_lower_id_proposal():
    result = analyse(load_armor(FIXTURE), crafted_level_protect=10)
    group = next(group for group in result.groups if group.hash == "770")

    assert group.preferred_survivor_id == "5062"
    assert [member.id for member in group.members] == ["5062", "5061"]
    assert [member.disposition for member in group.members] == [
        "preferred_survivor",
        "proposed_junk",
    ]


def test_analysis_group_and_member_order_is_stable_under_reversal():
    forward = analyse(load_armor(FIXTURE), crafted_level_protect=10)
    reversed_ = analyse(
        load_armor(FIXTURE).iloc[::-1], crafted_level_protect=10
    )
    assert forward.groups == reversed_.groups
    assert [
        (decision.id, decision.action, decision.note)
        for decision in forward.decisions
    ] == [
        (decision.id, decision.action, decision.note)
        for decision in reversed_.decisions
    ]


def test_tuning_mod_slot_uses_explicit_unknown_label_for_unrecognised_values():
    armor = load_armor(FIXTURE)
    armor.loc[armor["Id"] == "5001", "Tuning Stat"] = "future socket"
    armor.loc[armor["Id"] == "5002", "Tuning Stat"] = "future socket"
    group = next(
        group
        for group in analyse(armor, crafted_level_protect=10).groups
        if group.hash == "700"
    )
    assert group.tuning_mod_slot == "none/unknown"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("weapons", "Weapons"),
        ("health", "Health"),
        ("class", "Class"),
        ("grenade", "Grenade"),
        ("super", "Super"),
        ("melee", "Melee"),
        ("", "none/unknown"),
        ("future socket", "none/unknown"),
    ],
)
def test_tuning_mod_slot_projects_all_supported_values(raw, expected):
    armor = load_armor(FIXTURE)
    armor.loc[armor["Id"].isin(["5001", "5002"]), "Tuning Stat"] = raw
    group = next(
        group
        for group in analyse(armor, crafted_level_protect=10).groups
        if group.hash == "700"
    )
    assert group.tuning_mod_slot == expected


def test_group_projection_includes_spirit_identity_and_display_metadata():
    armor = load_armor(FIXTURE)
    mask = armor["Id"].isin(["5031", "5032"])
    armor.loc[mask, "Seasonal Mod"] = "seasonal-7"
    armor.loc[mask, "Holofoil"] = "artifice"
    armor.loc[mask, "Archetype"] = "melee-primary"
    group = next(
        group
        for group in analyse(armor, crafted_level_protect=10).groups
        if group.hash == "730"
    )
    assert group.name == "Exotic Mark"
    assert group.type == "Titan Mark"
    assert group.guardian_class == "Titan"
    assert group.item_archetype == "melee-primary"
    assert group.seasonal_mod == "seasonal-7"
    assert group.holofoil == "artifice"
    assert group.spirit_signature == (
        "Spirit of Contact",
        "Spirit of the Assassin",
    )
    assert group.preferred_survivor_id == "5031"


def test_group_projection_preserves_hash_and_spirit_safety_boundaries():
    result = analyse(load_armor(FIXTURE), crafted_level_protect=10)
    hashes = {group.hash for group in result.groups}
    assert "830" in hashes  # plain exotics legitimately group without Spirits
    assert "740" not in hashes and "741" not in hashes  # same name, new Hash
    assert "820" not in hashes  # spiritless exotic class items are unknown
    assert "840" not in hashes  # truncated Spirit signatures are unknown
