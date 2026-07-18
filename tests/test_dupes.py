from pathlib import Path

from vault_cleaner.parse import load_weapons
from vault_cleaner.rules.dupes import resolve

FIXTURE = Path(__file__).parent / "fixtures" / "weapons_dupes.csv"


def decisions():
    return resolve(load_weapons(FIXTURE), crafted_level_protect=10)


def by_id(ds):
    return {d.id: d for d in ds}


def test_best_copy_survives_and_lower_plain_copy_is_junked():
    d = by_id(decisions())
    assert "3001" not in d  # best copy: no output row at all
    assert d["3002"].action == "junk"
    assert d["3002"].tag == "junk"
    assert d["3002"].best_id == "3001"


def test_junk_note_appends_to_existing_notes():
    d = by_id(decisions())
    assert d["3002"].note == "old note #vc-junk: dupe-lower, best 3001"


def test_locked_dupe_is_review_not_junk():
    d = by_id(decisions())
    assert d["3003"].action == "review"
    assert d["3003"].tag == ""  # existing (empty) tag preserved
    assert "#vc-review: dupe-lower (locked)" in d["3003"].note


def test_hard_protected_copies_get_no_row():
    d = by_id(decisions())
    assert "3004" not in d  # tagged keep
    assert "3005" not in d  # equipped


def test_exotic_dupe_is_review_not_junk():
    d = by_id(decisions())
    assert d["3012"].action == "review"
    assert "(exotic)" in d["3012"].note
    assert d["3012"].best_id == "3011"


def test_single_copies_untouched():
    assert "3015" not in by_id(decisions())


def test_crafted_above_threshold_skipped_but_low_level_junked():
    d = by_id(decisions())
    assert "3021" not in d  # crafted level 12 — hard rail
    assert d["3022"].action == "junk"


def test_gear_tier_outranks_masterwork():
    d = by_id(decisions())
    assert "3031" not in d  # Tier 5 beats Tier 4 despite MW 0 vs 10
    assert d["3032"].action == "junk"
    assert d["3032"].best_id == "3031"


def test_groups_are_by_hash_never_name():
    # All "Dupe Rifle" decisions reference hash 500 only; a same-name
    # different-hash item must never appear in the group.
    for d in decisions():
        if d.name == "Dupe Rifle":
            assert d.hash == "500"
