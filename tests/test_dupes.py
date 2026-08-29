from pathlib import Path

import pandas as pd

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
    assert d["3002"].note == "old note #vc-junk: dupe-lower, kept 3001"


def test_locked_dupe_is_review_not_junk():
    d = by_id(decisions())
    assert d["3003"].action == "review"
    assert d["3003"].tag == ""  # existing (empty) tag preserved
    assert "#vc-review: dupe-lower (locked), kept 3001" in d["3003"].note


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
    assert "#vc-junk: dupe-tie, kept 3041" in d["3042"].note


def test_tied_exotics_review_flagged_as_tie_not_lower():
    d = by_id(decisions())
    assert "3051" not in d
    assert d["3052"].action == "review"
    assert "#vc-review: dupe-tie (exotic), kept 3051" in d["3052"].note


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
    assert ds["6104"].note.endswith("dupe-lower, kept 6101")


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


def test_base_and_enhanced_perk_names_share_identity():
    first = _roll_row("1", **{"Perks 3": "Range*"})
    second = _roll_row("2", **{"Perks 3": "Enhanced Range*"})

    assert exact_roll_fingerprint(pd.Series(first)) == exact_roll_fingerprint(
        pd.Series(second)
    )


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
