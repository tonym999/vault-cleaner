"""Smoke test for the committed sanitised real-export fixtures, and tests
for the CI guard (scripts/check_real_fixtures.py) that protects them (#181).
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

from vault_cleaner.parse import load_armor, load_ghosts, load_weapons

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
REAL_FIXTURES = Path(__file__).parent / "fixtures" / "real"
SNAPSHOT = REAL_FIXTURES / "2026-09-01T-current"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


grammar = _load_module("check_real_fixtures", SCRIPTS / "check_real_fixtures.py")
se = _load_module("sanitize_export", SCRIPTS / "sanitize_export.py")


# ---------------------------------------------------------------------------
# Smoke test on the committed fixtures.
# ---------------------------------------------------------------------------


def test_committed_fixtures_load_through_the_normal_parsers():
    weapons = load_weapons(SNAPSHOT / "weapons.csv")
    armor = load_armor(SNAPSHOT / "armor.csv")
    ghosts = load_ghosts(SNAPSHOT / "ghosts.csv")
    assert len(weapons) == 665
    assert len(armor) == 893
    assert len(ghosts) == 28
    for df in (weapons, armor, ghosts):
        assert df["Id"].str.fullmatch(r"1000[0-9]{15}").all()


def test_committed_provenance_row_counts_match():
    doc = json.loads((SNAPSHOT / "provenance.json").read_text(encoding="utf-8"))
    assert doc["files"]["weapons.csv"]["rows"] == 665
    assert doc["files"]["armor.csv"]["rows"] == 893
    assert doc["files"]["ghosts.csv"]["rows"] == 28
    assert doc["parity_modes"] == ["no-wishlists", "wishlists"]


def test_committed_fixtures_pass_the_ci_guard():
    assert grammar.check(REAL_FIXTURES) == []


def test_sanitiser_uses_the_guards_own_grammar_objects_not_copies():
    # #181's single-source-of-grammar contract: sanitize_export.py must
    # import these, never redefine structurally-identical copies.
    assert se.grammar is grammar
    assert se.ID_MARKER is grammar.ID_MARKER
    assert se.FAKE_ID is grammar.FAKE_ID
    assert se.RAWSID_PARTS_RE is grammar.RAWSID_PARTS_RE
    assert se.LOADOUTS_RE is grammar.LOADOUTS_RE
    assert se.recognise_and_canonicalise is grammar.recognise_and_canonicalise
    assert se.is_retained_or_placeholder is grammar.is_retained_or_placeholder


# ---------------------------------------------------------------------------
# CI guard tests, each on a tmp_path tree.
# ---------------------------------------------------------------------------


def _write_csv(
    path: Path,
    *,
    id_: str = "1000000000000000001",
    notes: str = "",
    loadouts: str = "",
    kill_tracker: str = "0",
    name: str = "N",
) -> None:
    # "Name" is a column the guard never validates the format of, only used
    # here to plant a byte-level-only defect in a non-Notes, non-Loadouts,
    # non-Id column.
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["Id", "Name", "Notes", "Loadouts", "Kill Tracker"])
        writer.writerow([f'"{id_}"', name, notes, loadouts, kill_tracker])


def _write_tree(root: Path, *, snapshot: str = "snap", provenance: dict | None = None, **csv_kwargs) -> Path:
    snap_dir = root / snapshot
    snap_dir.mkdir(parents=True)
    for name in ("weapons.csv", "armor.csv", "ghosts.csv"):
        _write_csv(snap_dir / name, **csv_kwargs)
    doc = {
        "files": {
            name: {"raw_sha256": "0" * 64, "rows": 1}
            for name in ("weapons.csv", "armor.csv", "ghosts.csv")
        },
        "parity_modes": ["no-wishlists"],
        "run_date": "2026-09-27",
        "script_version": 1,
    }
    if provenance is not None:
        doc = provenance
    (snap_dir / "provenance.json").write_text(
        json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return root


def _assert_rule_fires(errors: list[str], expected_substring: str) -> None:
    """Assert at least one reported error names ``expected_substring``."""
    assert any(expected_substring in e for e in errors), (expected_substring, errors)


def _assert_only_rule(errors: list[str], expected_substring: str) -> None:
    """Assert the guard trips on ``expected_substring`` and *only* that rule.

    Stricter than ``_assert_rule_fires``: the crafted input for this case
    must be clean everywhere except the one defect under test, so no other
    rule can also fire on it. A test that could be caught by a different
    rule too would still pass a bare ``!= []`` assertion even if the
    specific rule under test were disabled by a mutation — this pins which
    rule fired, keeping the guard's rules independently exercised and
    separable (#181 review finding B).
    """
    assert errors, f"expected an error containing {expected_substring!r}, got none"
    assert all(expected_substring in e for e in errors), (expected_substring, errors)


def test_a_valid_tree_passes(tmp_path):
    root = _write_tree(tmp_path)
    assert grammar.check(root) == []


def test_missing_root_passes(tmp_path):
    assert grammar.check(tmp_path / "does-not-exist") == []


def test_unmarked_id_fails(tmp_path):
    # A full 19-digit unmarked id also trips the byte-level long-digit-run
    # rule on the same cell — both rules legitimately co-fire here, so this
    # case only asserts the Id rule is among them (see the 15-digit case
    # below for a single-rule Id trip).
    root = _write_tree(tmp_path, id_="6900000000000000001")
    _assert_rule_fires(grammar.check(root), "Id lacks the")


def test_unmarked_15_digit_id_fails(tmp_path):
    # Too short to be a fake id at all (FAKE_ID is exactly 19 digits): must
    # still trip the Id rule, not silently pass as "not long enough to
    # check" or be caught only by the byte-level long-digit-run scan.
    root = _write_tree(tmp_path, id_="123456789012345")
    _assert_only_rule(grammar.check(root), "Id lacks the")


def test_unmarked_long_digit_run_in_notes_fails(tmp_path):
    # This unmarked id in free-form Notes text also trips the Notes-grammar
    # rule (it isn't a placeholder either) — both legitimately co-fire; the
    # column-specific case below is the clean single-rule byte-level trip.
    root = _write_tree(tmp_path, notes="see 6900000000000000099 for history")
    _assert_rule_fires(grammar.check(root), "unmarked long digit run")


def test_unmarked_long_digit_run_outside_notes_column_fails(tmp_path):
    # The byte-level >=16-digit scan covers the whole file, not just Notes:
    # a leaked real id in some other, unvalidated column (here Name), with a
    # correctly-marked Id and empty Notes/Loadouts, must still trip the
    # byte-level rule specifically — no other rule can see this column.
    root = _write_tree(tmp_path, name="6900000000000000099")
    _assert_only_rule(grammar.check(root), "unmarked long digit run")


def test_raw_multiline_owner_text_in_notes_fails(tmp_path):
    root = _write_tree(tmp_path, notes="line one\nline two, owner's own words")
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_clause_shaped_owner_note_fails(tmp_path):
    root = _write_tree(
        tmp_path, notes="#vc-review: armor-similar to 1000000000000000001 (private note)"
    )
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_owner_number_in_max_stat_delta_slot_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-review: armor-similar to 1000000000000000001 (max stat delta 3141592, total 1)",
    )
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_owner_number_in_curated_matches_slot_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes=(
            "#vc-review: coverage-dominated by; compare [id …0001]; "
            "curated matches 123456789 vs 1; partner largest coverage gain"
        ),
    )
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_non_zero_armor_score_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-junk: armor-score 64.2857 < floor 65 (best: melee_primary, rank 7/9 titan helmet)",
    )
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_reference_with_extra_part_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-junk: dupe-lower; keep [id …0001; location Vault]; winner lock",
    )
    _assert_only_rule(grammar.check(root), "Notes contains text outside")


def test_raw_loadout_name_fails(tmp_path):
    root = _write_tree(tmp_path, loadouts="My Real Loadout Name")
    _assert_only_rule(grammar.check(root), "Loadouts is not a sanitised format")


def test_non_zero_kill_tracker_fails(tmp_path):
    root = _write_tree(tmp_path, kill_tracker="42")
    _assert_only_rule(grammar.check(root), "Kill Tracker is not zeroed")


def test_provenance_extra_key_fails(tmp_path):
    doc = {
        "files": {
            name: {"raw_sha256": "0" * 64, "rows": 1}
            for name in ("weapons.csv", "armor.csv", "ghosts.csv")
        },
        "parity_modes": ["no-wishlists"],
        "run_date": "2026-09-27",
        "script_version": 1,
        "extra_key": "surprise",
    }
    root = _write_tree(tmp_path, provenance=doc)
    _assert_only_rule(grammar.check(root), "must have exactly the keys")


def test_provenance_wrong_row_count_fails(tmp_path):
    doc = {
        "files": {
            name: {"raw_sha256": "0" * 64, "rows": 99}
            for name in ("weapons.csv", "armor.csv", "ghosts.csv")
        },
        "parity_modes": ["no-wishlists"],
        "run_date": "2026-09-27",
        "script_version": 1,
    }
    root = _write_tree(tmp_path, provenance=doc)
    _assert_only_rule(grammar.check(root), "does not match the CSV's data-row count")


def _valid_provenance_except(**override) -> dict:
    doc = {
        "files": {
            name: {"raw_sha256": "0" * 64, "rows": 1}
            for name in ("weapons.csv", "armor.csv", "ghosts.csv")
        },
        "parity_modes": ["no-wishlists"],
        "run_date": "2026-09-27",
        "script_version": 1,
    }
    doc.update(override)
    return doc


def test_provenance_run_date_bad_format_fails(tmp_path):
    root = _write_tree(tmp_path, provenance=_valid_provenance_except(run_date="09/27/2026"))
    _assert_only_rule(grammar.check(root), "run_date does not match YYYY-MM-DD")


def test_provenance_run_date_invalid_calendar_date_fails(tmp_path):
    root = _write_tree(tmp_path, provenance=_valid_provenance_except(run_date="2026-13-45"))
    _assert_only_rule(grammar.check(root), "run_date is not a valid calendar date")


def test_provenance_parity_modes_not_an_accepted_form_fails(tmp_path):
    root = _write_tree(tmp_path, provenance=_valid_provenance_except(parity_modes=["wishlists"]))
    _assert_only_rule(grammar.check(root), "parity_modes is not one of the accepted forms")


def test_provenance_script_version_wrong_type_fails(tmp_path):
    root = _write_tree(tmp_path, provenance=_valid_provenance_except(script_version="1"))
    _assert_only_rule(grammar.check(root), "script_version is not the integer 1")


def test_provenance_script_version_bool_fails(tmp_path):
    # bool is a subclass of int in Python: True == 1 must still be rejected.
    root = _write_tree(tmp_path, provenance=_valid_provenance_except(script_version=True))
    _assert_only_rule(grammar.check(root), "script_version is not the integer 1")


def test_stray_file_fails(tmp_path):
    root = _write_tree(tmp_path)
    (root / "snap" / "stray.txt").write_text("not ours", encoding="utf-8")
    _assert_only_rule(grammar.check(root), "unexpected file")


def test_valid_csv_under_a_stray_file_name_fails(tmp_path):
    # A file that is a byte-for-byte-valid sanitised CSV under a name the
    # guard doesn't recognise: content-level rules must not paper over a
    # filename that isn't one of the four known names.
    root = _write_tree(tmp_path)
    good_bytes = (root / "snap" / "weapons.csv").read_bytes()
    (root / "snap" / "weapons_extra.csv").write_bytes(good_bytes)
    _assert_only_rule(grammar.check(root), "unexpected file")


# No rule-decision assertions on the real fixtures: out of scope for #181
# (the fixtures are for future rule-test adoption, not this ticket).
