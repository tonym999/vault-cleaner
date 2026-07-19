from pathlib import Path

import pytest

from vault_cleaner.parse import SchemaError, load_armor
from vault_cleaner.rules.armor_dupes import fingerprint, run, spirit_signature

FIXTURE = Path(__file__).parent / "fixtures" / "armor_dupes.csv"


def decisions(frame=None):
    return run(frame if frame is not None else load_armor(FIXTURE), crafted_level_protect=10)


def by_id(ds):
    return {d.id: d for d in ds}


def test_higher_masterwork_survives_and_loser_junked_with_note_appended():
    d = by_id(decisions())
    assert "5001" not in d  # survivor: no output row
    assert d["5002"].action == "junk"
    assert d["5002"].tag == "junk"
    assert d["5002"].note == "old note #vc-junk: armor-exact-dupe, kept 5001"


def test_loadout_referenced_loser_reviews_never_junk():
    # DIM loadouts pin instance ids — junking a loadout member breaks the
    # loadout even when an identical twin survives
    d = by_id(decisions())
    assert "5011" not in d  # hard-protected survivor (tagged keep)
    assert d["5012"].action == "review"
    assert d["5012"].tag == ""  # existing tag preserved
    assert "#vc-review: armor-exact-dupe (loadout), kept 5011" in d["5012"].note
    assert "5013" not in d  # equipped copy loses the id tie-break but is hard: no row


def test_tie_survivor_is_lowest_id_not_row_order():
    # fixture lists 5022 before 5021: export order must not pick the survivor
    d = by_id(decisions())
    assert "5021" not in d
    assert d["5022"].action == "junk"
    assert "#vc-junk: armor-exact-dupe-tie, kept 5021" in d["5022"].note


def test_reversing_the_csv_changes_nothing():
    forward = {(d.id, d.action, d.note) for d in decisions()}
    reversed_ = {(d.id, d.action, d.note) for d in decisions(load_armor(FIXTURE).iloc[::-1])}
    assert forward == reversed_


def test_exotic_loser_reviews_and_spirit_roll_splits_the_group():
    d = by_id(decisions())
    assert "5031" not in d  # best exotic copy survives
    assert d["5032"].action == "review"
    assert "#vc-review: armor-exact-dupe (exotic), kept 5031" in d["5032"].note
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


def test_loadout_membership_outranks_masterwork():
    d = by_id(decisions())
    assert "5081" not in d  # in a loadout, mw 0: still the survivor
    assert d["5082"].action == "junk"
    assert d["5082"].kept_id == "5081"


def test_lock_outranks_masterwork_and_locked_loser_reviews():
    d = by_id(decisions())
    assert "5091" not in d  # locked, mw 0: survivor over mw 5
    assert d["5092"].action == "junk"
    assert d["5092"].kept_id == "5091"
    # all-locked group: loser is soft-protected, reviews with the lock named
    assert "5101" not in d
    assert d["5102"].action == "review"
    assert "#vc-review: armor-exact-dupe (locked), kept 5101" in d["5102"].note


def test_spiritless_exotic_class_items_never_group():
    # No visible Spirit perks means the roll is unknown — an unknown roll
    # can't be proven identical to anything, so no grouping, no advice
    d = by_id(decisions())
    assert "5111" not in d and "5112" not in d


def test_plain_exotics_without_spirits_still_group():
    # Non-class-item exotics legitimately have no Spirit perks; the guard
    # must not exempt them from normal dupe grouping
    d = by_id(decisions())
    assert "5121" not in d  # survivor
    assert d["5122"].action == "review"
    assert "#vc-review: armor-exact-dupe (exotic), kept 5121" in d["5122"].note


def test_fingerprint_ignores_mutable_state():
    df = load_armor(FIXTURE).set_index("Id", drop=False)
    a, b = df.loc["5001"], df.loc["5002"]  # differ in mw/power/notes only
    assert fingerprint(a) == fingerprint(b)


def test_spirit_signature_reads_only_spirit_perks():
    df = load_armor(FIXTURE).set_index("Id", drop=False)
    assert spirit_signature(df.loc["5031"]) == ("Spirit of Contact", "Spirit of the Assassin")
    assert spirit_signature(df.loc["5001"]) == ()


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
