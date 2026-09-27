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
) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["Id", "Notes", "Loadouts", "Kill Tracker"])
        writer.writerow([f'"{id_}"', notes, loadouts, kill_tracker])


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


def test_a_valid_tree_passes(tmp_path):
    root = _write_tree(tmp_path)
    assert grammar.check(root) == []


def test_missing_root_passes(tmp_path):
    assert grammar.check(tmp_path / "does-not-exist") == []


def test_unmarked_id_fails(tmp_path):
    root = _write_tree(tmp_path, id_="6900000000000000001")
    assert grammar.check(root) != []


def test_unmarked_long_digit_run_in_notes_fails(tmp_path):
    root = _write_tree(tmp_path, notes="see 6900000000000000099 for history")
    assert grammar.check(root) != []


def test_raw_multiline_owner_text_in_notes_fails(tmp_path):
    root = _write_tree(tmp_path, notes="line one\nline two, owner's own words")
    assert grammar.check(root) != []


def test_clause_shaped_owner_note_fails(tmp_path):
    root = _write_tree(
        tmp_path, notes="#vc-review: armor-similar to 1000000000000000001 (private note)"
    )
    assert grammar.check(root) != []


def test_owner_number_in_max_stat_delta_slot_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-review: armor-similar to 1000000000000000001 (max stat delta 3141592, total 1)",
    )
    assert grammar.check(root) != []


def test_owner_number_in_curated_matches_slot_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes=(
            "#vc-review: coverage-dominated by; compare [id …0001]; "
            "curated matches 123456789 vs 1; partner largest coverage gain"
        ),
    )
    assert grammar.check(root) != []


def test_non_zero_armor_score_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-junk: armor-score 64.2857 < floor 65 (best: melee_primary, rank 7/9 titan helmet)",
    )
    assert grammar.check(root) != []


def test_reference_with_extra_part_fails(tmp_path):
    root = _write_tree(
        tmp_path,
        notes="#vc-junk: dupe-lower; keep [id …0001; location Vault]; winner lock",
    )
    assert grammar.check(root) != []


def test_raw_loadout_name_fails(tmp_path):
    root = _write_tree(tmp_path, loadouts="My Real Loadout Name")
    assert grammar.check(root) != []


def test_non_zero_kill_tracker_fails(tmp_path):
    root = _write_tree(tmp_path, kill_tracker="42")
    assert grammar.check(root) != []


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
    assert grammar.check(root) != []


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
    assert grammar.check(root) != []


def test_stray_file_fails(tmp_path):
    root = _write_tree(tmp_path)
    (root / "snap" / "stray.txt").write_text("not ours", encoding="utf-8")
    assert grammar.check(root) != []


# No rule-decision assertions on the real fixtures: out of scope for #181
# (the fixtures are for future rule-test adoption, not this ticket).
