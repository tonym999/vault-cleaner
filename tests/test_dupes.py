from pathlib import Path

import pandas as pd
import pytest

from vault_cleaner.parse import load_weapons
from vault_cleaner.rules.dupes import exact_roll_fingerprint, resolve

FIXTURE = Path(__file__).parent / "fixtures" / "weapons_dupes.csv"
SLAMMER_FIXTURE = Path(__file__).parent / "fixtures" / "weapons_slammer_like.csv"


def decisions():
    return resolve(load_weapons(FIXTURE), crafted_level_protect=10)


def by_id(ds):
    return {d.id: d for d in ds}


def test_best_copy_survives_and_lower_plain_copy_is_junked():
    d = by_id(decisions())
    assert "3001" not in d  # best copy: no output row at all
    assert d["3002"].action == "junk"
    assert d["3002"].tag == "junk"
    assert d["3002"].kept_id == "3001"


def test_junk_note_appends_to_existing_notes():
    d = by_id(decisions())
    assert d["3002"].note == (
        "old note #vc-junk: dupe-lower; keep [id 3001; owner Vault; Tier 5; "
        "MW10; roll Mag B / Trait A]; winner higher Masterwork Tier"
    )


def test_locked_dupe_is_review_not_junk():
    d = by_id(decisions())
    assert d["3003"].action == "review"
    assert d["3003"].tag == ""  # existing (empty) tag preserved
    assert "#vc-review: dupe-lower (locked); keep [id 3001" in d["3003"].note


def test_hard_protected_copies_get_no_row():
    d = by_id(decisions())
    assert "3004" not in d  # tagged keep
    assert "3005" not in d  # equipped


def test_exotic_dupe_is_review_not_junk():
    d = by_id(decisions())
    assert d["3012"].action == "review"
    assert "(exotic)" in d["3012"].note
    assert d["3012"].kept_id == "3011"


def test_single_copies_untouched():
    assert "3015" not in by_id(decisions())


def test_crafted_at_and_above_threshold_skipped_but_low_level_junked():
    d = by_id(decisions())
    assert "3021" not in d  # crafted level 12 — hard rail
    assert "3023" not in d  # crafted level 10 — hard rail boundary
    assert d["3022"].action == "junk"  # crafted level 2 continues normally


def test_gear_tier_outranks_masterwork():
    d = by_id(decisions())
    assert "3031" not in d  # Tier 5 beats Tier 4 despite MW 0 vs 10
    assert d["3032"].action == "junk"
    assert d["3032"].kept_id == "3031"
    assert "winner higher Tier" in d["3032"].note


def test_crafted_level_is_explained_after_tier_and_masterwork():
    rows = _roll_df(
        _roll_row("1", Crafted="crafted", **{"Crafted Level": "4"}),
        _roll_row("2", Crafted="crafted", **{"Crafted Level": "3"}),
    )

    decisions = by_id(resolve(rows, crafted_level_protect=10))

    assert decisions["2"].kept_id == "1"
    assert "winner higher Crafted Level" in decisions["2"].note


def test_groups_are_by_hash_never_name():
    # All "Dupe Rifle" decisions reference hash 500 only; a same-name
    # different-hash item must never appear in the group.
    for d in decisions():
        if d.name == "Dupe Rifle":
            assert d.hash == "500"


def test_tied_plain_copies_earlier_kept_later_junked_as_tie():
    d = by_id(decisions())
    assert "3041" not in d  # lowest opaque id wins the deterministic tie
    assert d["3042"].action == "junk"
    assert "#vc-junk: dupe-tie; keep [id 3041" in d["3042"].note
    assert "winner deterministic id tie-break" in d["3042"].note


def test_tied_exotics_review_flagged_as_tie_not_lower():
    d = by_id(decisions())
    assert "3051" not in d
    assert d["3052"].action == "review"
    assert "#vc-review: dupe-tie (exotic); keep [id 3051" in d["3052"].note


def _roll_row(item_id, item_hash="900", *, rarity="Legendary", **values):
    row = {
        "Name": "Synthetic Weapon",
        "Hash": item_hash,
        "Id": item_id,
        "Tag": "",
        "Rarity": rarity,
        "Tier": "5",
        "Type": "Sword",
        "Locked": "false",
        "Equipped": "false",
        "Crafted": "false",
        "Crafted Level": "0",
        "Masterwork Tier": "0",
        "Notes": "",
        "Owner": "Vault",
    }
    row.update({f"Perks {i}": f"Roll {i}" for i in range(21)})
    row["Perks 6"] = "Kill Tracker"
    row.update(values)
    return row


def _roll_df(*rows):
    return pd.DataFrame(rows).fillna("").astype(str)


def test_slammer_fixture_keeps_distinct_same_hash_rolls_and_exact_copy():
    ds = by_id(resolve(load_weapons(SLAMMER_FIXTURE), crafted_level_protect=10))

    assert set(ds) == {"6104"}
    assert ds["6104"].action == "junk"
    assert ds["6104"].kept_id == "6101"
    assert "dupe-lower; keep [id 6101" in ds["6104"].note


def test_narrower_contiguous_prefix_still_resolves_exact_duplicates():
    rows = _roll_df(
        _roll_row("1", **{"Masterwork Tier": "10"}),
        _roll_row("2"),
    ).drop(columns=[f"Perks {slot}" for slot in range(7, 21)])

    decisions = resolve(rows, crafted_level_protect=10)

    assert [(decision.id, decision.kept_id) for decision in decisions] == [
        ("2", "1")
    ]


def test_wider_contiguous_prefix_remains_groupable():
    row = pd.Series(_roll_row("1"))

    fingerprint = exact_roll_fingerprint(row)

    assert fingerprint is not None
    assert len(fingerprint) == 6


def test_reversing_slammer_rows_preserves_all_decision_fields():
    original = load_weapons(SLAMMER_FIXTURE)
    forward = resolve(original, crafted_level_protect=10)
    reverse = resolve(original.iloc[::-1], crafted_level_protect=10)

    fields = ("id", "kept_id", "action", "tag", "note")
    assert [tuple(getattr(d, field) for field in fields) for d in forward] == [
        tuple(getattr(d, field) for field in fields) for d in reverse
    ]


def test_same_hash_different_roll_fingerprints_do_not_compete():
    rows = _roll_df(
        _roll_row("1", **{"Perks 3": "Role A*"}),
        _roll_row("2", **{"Perks 3": "Role B*"}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) != exact_roll_fingerprint(rows.iloc[1])
    assert resolve(rows, crafted_level_protect=10) == []


def test_only_one_trailing_marker_is_removed_from_identity_cells():
    one_marker = _roll_df(
        _roll_row("1", **{"Perks 3": "Trait*"})
    ).iloc[0]
    two_markers = _roll_df(
        _roll_row("2", **{"Perks 3": "Trait**"})
    ).iloc[0]

    first = exact_roll_fingerprint(one_marker)
    second = exact_roll_fingerprint(two_markers)

    assert first is not None and second is not None
    assert first != second
    assert first[3] == "trait"
    assert second[3] == "trait*"
    assert resolve(
        _roll_df(
            _roll_row("1", **{"Perks 3": "Trait*"}),
            _roll_row("2", **{"Perks 3": "Trait**"}),
        ),
        crafted_level_protect=10,
    ) == []


def test_double_marker_tracker_is_not_a_measured_boundary():
    rows = _roll_df(
        _roll_row("1", **{"Perks 6": "Kill Tracker**"}),
        _roll_row("2", **{"Perks 6": "Kill Tracker**"}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is None
    assert exact_roll_fingerprint(rows.iloc[1]) is None
    assert resolve(rows, crafted_level_protect=10) == []


def test_exotic_same_hash_different_roll_fingerprints_do_not_compete():
    rows = _roll_df(
        _roll_row(
            "1", item_hash="950", rarity="Exotic", **{"Perks 0": "Frame A*"}
        ),
        _roll_row(
            "2", item_hash="950", rarity="Exotic", **{"Perks 0": "Frame B*"}
        ),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) != exact_roll_fingerprint(
        rows.iloc[1]
    )
    assert resolve(rows, crafted_level_protect=10) == []


def test_gapped_perk_headers_are_not_a_partial_identity():
    row = _roll_row("1", **{"Perks 6": "Socket 6", "Perks 12": "Kill Tracker"})
    rows = _roll_df(row).drop(columns=["Perks 11"])

    assert exact_roll_fingerprint(rows.iloc[0]) is None


def test_missing_perk_start_is_not_a_partial_identity():
    row = _roll_df(_roll_row("1")).drop(columns=["Perks 0"])

    assert exact_roll_fingerprint(row.iloc[0]) is None


@pytest.mark.parametrize(
    "tracker_cell",
    ["Tracker Disabled,Kill Tracker", "Kill Tracker,Crucible Tracker"],
)
def test_comma_bearing_tracker_candidates_are_not_grouped(tracker_cell):
    rows = _roll_df(
        _roll_row("1", **{"Perks 6": tracker_cell}),
        _roll_row("2", **{"Perks 6": tracker_cell}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is None
    assert exact_roll_fingerprint(rows.iloc[1]) is None
    assert resolve(rows, crafted_level_protect=10) == []


def test_internal_star_tracker_candidate_is_not_grouped():
    tracker_cell = "Kill Tracker*,Tracker Disabled"
    rows = _roll_df(
        _roll_row("1", **{"Perks 3": tracker_cell}),
        _roll_row("2", **{"Perks 3": tracker_cell}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is None
    assert exact_roll_fingerprint(rows.iloc[1]) is None
    assert resolve(rows, crafted_level_protect=10) == []


def test_comma_bearing_tracker_candidate_in_frame_is_not_grouped():
    tracker_cell = "Kill Tracker*,Frame"
    rows = _roll_df(
        _roll_row("1", **{"Perks 0": tracker_cell}),
        _roll_row("2", **{"Perks 0": tracker_cell}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is None
    assert exact_roll_fingerprint(rows.iloc[1]) is None
    assert resolve(rows, crafted_level_protect=10) == []


def test_legitimate_comma_name_is_groupable_and_resolves():
    rows = _roll_df(
        _roll_row("1", **{"Perks 3": "Nail, Meet Hammer*"}),
        _roll_row("2", **{"Perks 3": "Nail, Meet Hammer"}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is not None
    assert [(decision.id, decision.kept_id) for decision in resolve(
        rows, crafted_level_protect=10
    )] == [("2", "1")]

    arbitrary_tracker_rows = _roll_df(
        _roll_row("3", **{"Perks 3": "Treasure Tracker, Variant"}),
        _roll_row("4", **{"Perks 3": "Treasure Tracker, Variant"}),
    )
    assert exact_roll_fingerprint(arbitrary_tracker_rows.iloc[0]) is not None
    assert len(resolve(arbitrary_tracker_rows, crafted_level_protect=10)) == 1


def test_legitimate_comma_frame_name_is_groupable_and_resolves():
    rows = _roll_df(
        _roll_row("1", **{"Perks 0": "Frame, Variant*"}),
        _roll_row("2", **{"Perks 0": "Frame, Variant"}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is not None
    assert len(resolve(rows, crafted_level_protect=10)) == 1


def test_same_name_different_hashes_do_not_group():
    rows = _roll_df(
        _roll_row("1", item_hash="900"),
        _roll_row("2", item_hash="901"),
    )

    assert rows.iloc[0]["Name"] == rows.iloc[1]["Name"]
    assert resolve(rows, crafted_level_protect=10) == []


def test_selected_markers_and_multi_option_cells_do_not_split_identity():
    first = _roll_row(
        "1",
        **{"Perks 1": "Barrel A*", "Perks 2": "Barrel B"},
    )
    second = _roll_row(
        "2",
        **{"Perks 1": "Barrel A", "Perks 2": "Barrel B*"},
    )

    # The adjacent cells are one measured multi-option socket; only the
    # selected marker moved, so the available roll options stay identical.
    assert exact_roll_fingerprint(pd.Series(first)) == exact_roll_fingerprint(
        pd.Series(second)
    )


def test_enhanced_perk_name_is_not_collapsed_to_base_name():
    first = _roll_row("1", **{"Perks 3": "Battery*"})
    second = _roll_row("2", **{"Perks 3": "Enhanced Battery*"})

    assert exact_roll_fingerprint(pd.Series(first)) != exact_roll_fingerprint(
        pd.Series(second)
    )
    assert resolve(_roll_df(first, second), crafted_level_protect=10) == []


def test_mutable_cells_after_tracker_do_not_split_identity():
    first = _roll_row(
        "1",
        **{"Perks 7": "Dawning Memento*", "Perks 8": "Tier 5: Range*"},
    )
    second = _roll_row(
        "2",
        **{"Perks 7": "Gambit Memento*", "Perks 8": "Tier 1: Range*"},
    )

    assert exact_roll_fingerprint(pd.Series(first)) == exact_roll_fingerprint(
        pd.Series(second)
    )
    assert len(resolve(_roll_df(first, second), crafted_level_protect=10)) == 1


def test_missing_or_unknown_roll_identity_fails_safe():
    missing_boundary = _roll_row("1", **{"Perks 6": "Unknown Socket"})
    missing_prefix = _roll_row("2", **{"Perks 3": "", "Perks 6": "Kill Tracker"})
    unknown_rarity = _roll_row("3", rarity="Common")
    blank_hash = _roll_row("4", item_hash="")

    assert exact_roll_fingerprint(pd.Series(missing_boundary)) is None
    assert exact_roll_fingerprint(pd.Series(missing_prefix)) is None
    assert exact_roll_fingerprint(pd.Series(unknown_rarity)) is None
    assert exact_roll_fingerprint(pd.Series(blank_hash)) is None
    assert resolve(
        _roll_df(missing_boundary, missing_prefix, unknown_rarity, blank_hash),
        crafted_level_protect=10,
    ) == []


@pytest.mark.parametrize("gameplay_tracker", ["Treasure Tracker", "Resource Tracker"])
def test_unknown_gameplay_tracker_name_stays_in_identity_before_valid_boundary(
    gameplay_tracker,
):
    first = _roll_row(
        "1",
        **{
            "Perks 3": gameplay_tracker,
            "Perks 4": "Later Prefix A",
            "Perks 6": "Kill Tracker",
        },
    )
    second = _roll_row(
        "2",
        **{
            "Perks 3": gameplay_tracker,
            "Perks 4": "Later Prefix B",
            "Perks 6": "Kill Tracker",
        },
    )

    assert exact_roll_fingerprint(pd.Series(first)) != exact_roll_fingerprint(
        pd.Series(second)
    )
    assert resolve(_roll_df(first, second), crafted_level_protect=10) == []


def test_unknown_tracker_label_without_measured_boundary_is_ungroupable():
    first = _roll_row("1", **{"Perks 6": "Vanguard Tracker"})
    second = _roll_row("2", **{"Perks 6": "Vanguard Tracker"})

    assert exact_roll_fingerprint(pd.Series(first)) is None
    assert exact_roll_fingerprint(pd.Series(second)) is None
    assert resolve(_roll_df(first, second), crafted_level_protect=10) == []


@pytest.mark.parametrize("tracker_label", ["Kill Tracker", "Crucible Tracker"])
def test_measured_tracker_labels_are_valid_boundaries(tracker_label):
    first = _roll_row("1", **{"Perks 6": f"{tracker_label}*"})
    second = _roll_row("2", **{"Perks 6": tracker_label.casefold()})

    assert exact_roll_fingerprint(pd.Series(first)) is not None
    assert len(resolve(_roll_df(first, second), crafted_level_protect=10)) == 1


@pytest.mark.parametrize(
    "tracker_cell",
    [
        "Kill Tracker*,Ordinary Name",
        "Ordinary Name,Crucible Tracker*",
    ],
)
def test_comma_measured_tracker_components_reject_any_order_and_marker(
    tracker_cell,
):
    rows = _roll_df(
        _roll_row("1", **{"Perks 3": tracker_cell}),
        _roll_row("2", **{"Perks 3": tracker_cell}),
    )

    assert exact_roll_fingerprint(rows.iloc[0]) is None
    assert exact_roll_fingerprint(rows.iloc[1]) is None
    assert resolve(rows, crafted_level_protect=10) == []
