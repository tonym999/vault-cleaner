"""Tests for scripts/sanitize_export.py (#181).

Everything here is synthetic: invented 19-digit ids beginning "69" (the
project convention for made-up long ids), and the project's own existing
synthetic rule-test fixtures with their ids remapped to that width so the
production rule emitters — not hand-rolled strings — produce the Notes
clauses this suite feeds through the sanitiser. The script and CI-guard
modules are loaded by path, exactly as the script itself loads the guard,
so these tests exercise the real objects, not copies.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

from vault_cleaner.config import load_config
from vault_cleaner.note_history import strip_trailing_tool_clauses
from vault_cleaner.parse import load_armor, load_ghosts, load_weapons
from vault_cleaner.rules import armor as armor_rules
from vault_cleaner.rules import armor_close, armor_dupes, dupes
from vault_cleaner.rules import ghosts as ghost_rules
from vault_cleaner.rules import weapons as weapons_rules
from vault_cleaner.rules.id_order import instance_id_order
from vault_cleaner.wishlist import parse_wishlist

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
FIXTURES = Path(__file__).parent / "fixtures"
CONFIG = REPO / "config.toml"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


grammar = _load_module("check_real_fixtures", SCRIPTS / "check_real_fixtures.py")
se = _load_module("sanitize_export", SCRIPTS / "sanitize_export.py")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _state_for_ids(ids) -> se.SanitiserState:
    unique_ids = sorted(set(ids), key=instance_id_order)
    id_map = se._build_id_map(unique_ids)
    return se.SanitiserState(id_map=id_map, export_ids=frozenset(unique_ids), next_fresh_rank=len(unique_ids) + 1)


def _extract_clause(decision, raw_notes: str) -> str:
    """The text a rule pass appended, isolated from the pre-existing Notes."""
    base = strip_trailing_tool_clauses(raw_notes)
    note = decision.note
    assert note.startswith(base), (note, base)
    return note[len(base):].strip()


def _assert_retained(text: str) -> None:
    assert any(p.fullmatch(text) for p in grammar.RETAINED_CLAUSE_RES), text
    # Canonical output must still be a complete clause to the production
    # recogniser — the subset relation the plan pins.
    assert strip_trailing_tool_clauses(text) == ""


def _remap_ids(df: pd.DataFrame, base: int) -> tuple[pd.DataFrame, dict[str, str]]:
    """Give a committed synthetic rule fixture 19-digit ids, order preserved."""
    df = df.copy()
    unique_old = list(dict.fromkeys(df["Id"].tolist()))
    mapping = {old: f"69{base + i:017d}" for i, old in enumerate(unique_old)}
    df["Id"] = df["Id"].map(mapping)
    return df, mapping


def _write_raw_csv(path: Path, df: pd.DataFrame) -> None:
    header = list(df.columns)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        for _, row in df.iterrows():
            writer.writerow([f'"{row[c]}"' if c == "Id" else row[c] for c in header])


def _build_snapshot(root: Path) -> tuple[Path, dict, dict, dict]:
    """A small, schema-complete, offline-safe raw snapshot: production fixtures
    (weapons_dupes.csv, armor_dupes.csv, ghosts_cleanup.csv), 19-digit ids."""
    snap = root / "snap"
    snap.mkdir(parents=True)
    weapons, wmap = _remap_ids(load_weapons(FIXTURES / "weapons_dupes.csv"), base=1)
    armor, amap = _remap_ids(load_armor(FIXTURES / "armor_dupes.csv"), base=101)
    ghosts, gmap = _remap_ids(load_ghosts(FIXTURES / "ghosts_cleanup.csv"), base=201)
    _write_raw_csv(snap / "weapons.csv", weapons)
    _write_raw_csv(snap / "armor.csv", armor)
    _write_raw_csv(snap / "ghosts.csv", ghosts)
    return snap, wmap, amap, gmap


# Minimal schema-complete rows for refusal/planted-leak tests, where only one
# thing should vary between runs.
_MIN_WEAPON_HEADER = [
    "Name", "Hash", "Id", "Tag", "Rarity", "Locked", "Equipped", "Notes",
    "Type", "Ammo", "Crafted", "Crafted Level", "Kill Tracker", "Perks 0",
    "Loadouts",
]
_MIN_ARMOR_HEADER = [
    "Name", "Hash", "Id", "Tag", "Rarity", "Locked", "Equipped", "Notes",
    "Type", "Equippable", "Loadouts", "Tuning Stat", "Seasonal Mod",
    "Holofoil", "Masterwork Tier", "Power", "Tier", "Perks 0", "Archetype",
    "Weapons (Base)", "Health (Base)", "Class (Base)", "Grenade (Base)",
    "Super (Base)", "Melee (Base)",
]
_MIN_GHOST_HEADER = [
    "Name", "Hash", "Id", "Tag", "Rarity", "Locked", "Equipped", "Notes",
    "Loadouts",
]


def _min_weapon_row(id_: str, hash_: str = "1", **kv) -> dict[str, str]:
    row = dict.fromkeys(_MIN_WEAPON_HEADER, "")
    row.update({
        "Name": "W", "Hash": hash_, "Id": id_, "Rarity": "Legendary",
        "Locked": "false", "Equipped": "false", "Type": "Auto Rifle",
        "Ammo": "Primary", "Crafted": "false", "Crafted Level": "0",
        "Kill Tracker": "0", "Perks 0": "Frame",
    })
    row.update(kv)
    return row


def _min_armor_row(id_: str, hash_: str = "2", **kv) -> dict[str, str]:
    row = dict.fromkeys(_MIN_ARMOR_HEADER, "")
    row.update({
        "Name": "A", "Hash": hash_, "Id": id_, "Rarity": "Legendary",
        "Locked": "false", "Equipped": "false", "Type": "Chest Armor",
        "Equippable": "Titan", "Holofoil": "false", "Masterwork Tier": "0",
        "Power": "0", "Tier": "5",
        "Weapons (Base)": "0", "Health (Base)": "0", "Class (Base)": "0",
        "Grenade (Base)": "0", "Super (Base)": "0", "Melee (Base)": "0",
    })
    row.update(kv)
    return row


def _min_ghost_row(id_: str, hash_: str = "3", **kv) -> dict[str, str]:
    row = dict.fromkeys(_MIN_GHOST_HEADER, "")
    row.update({
        "Name": "G", "Hash": hash_, "Id": id_, "Rarity": "Legendary",
        "Locked": "false", "Equipped": "false",
    })
    row.update(kv)
    return row


def _write_min_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([f'"{row[c]}"' if c == "Id" else row[c] for c in header])


def _min_snapshot(
    root: Path,
    *,
    weapon_rows=None,
    armor_rows=None,
    ghost_rows=None,
    weapon_header=None,
    skip=(),
) -> Path:
    snap = root / "snap"
    snap.mkdir(parents=True)
    if "weapons" not in skip:
        _write_min_csv(
            snap / "weapons.csv",
            weapon_header or _MIN_WEAPON_HEADER,
            weapon_rows if weapon_rows is not None else [_min_weapon_row("6900000000000000001")],
        )
    if "armor" not in skip:
        _write_min_csv(
            snap / "armor.csv",
            _MIN_ARMOR_HEADER,
            armor_rows if armor_rows is not None else [_min_armor_row("6900000000000000101")],
        )
    if "ghosts" not in skip:
        _write_min_csv(
            snap / "ghosts.csv",
            _MIN_GHOST_HEADER,
            ghost_rows if ghost_rows is not None else [_min_ghost_row("6900000000000000201")],
        )
    return snap


def _two_weapon_snapshot(root: Path, second_notes: str) -> tuple[Path, str, str]:
    id_a, id_b = "6900000000000000001", "6900000000000000002"
    snap = _min_snapshot(
        root,
        weapon_rows=[_min_weapon_row(id_a), _min_weapon_row(id_b, Notes=second_notes)],
    )
    return snap, id_a, id_b


# ---------------------------------------------------------------------------
# Transform units
# ---------------------------------------------------------------------------


def test_legacy_exact_kept_clause_rewritten_and_kept():
    # Family 1 is migration-only: no current emitter produces it.
    state = _state_for_ids(["6900000000000000001"])
    rendered = state.sanitize_notes("#vc-junk: dupe-lower, kept 6900000000000000001")
    assert rendered == f"#vc-junk: dupe-lower, kept {state.id_map['6900000000000000001']}"
    _assert_retained(rendered)


def test_legacy_armor_similar_clause_rewritten_and_kept():
    # Family 3 is migration-only.
    state = _state_for_ids(["6900000000000000001"])
    rendered = state.sanitize_notes(
        "#vc-review: armor-similar to 6900000000000000001 (max stat delta 3, total 5)"
    )
    assert "max stat delta 0, total 0" in rendered
    assert "3" not in rendered.split("(")[-1].replace("0", "")
    _assert_retained(rendered)


def test_legacy_armor_dominated_clause_rewritten_and_kept():
    # Family 4 is migration-only.
    state = _state_for_ids(["6900000000000000001"])
    rendered = state.sanitize_notes("#vc-review: armor-dominated by 6900000000000000001 (+7 total)")
    assert rendered == f"#vc-review: armor-dominated by {state.id_map['6900000000000000001']} (+0 total)"
    _assert_retained(rendered)


def test_notes_only_id_is_mapped():
    rows = {
        "weapons": [{"Id": "6900000000000000001", "Notes": "see 6900000000000099999 for history"}],
        "armor": [],
        "ghosts": [],
    }
    export_ids, notes_only_ids = se._collect_ids(rows)
    assert export_ids == frozenset({"6900000000000000001"})
    assert notes_only_ids == frozenset({"6900000000000099999"})


def test_owner_text_placeholder_preserves_newline_comma_quote():
    state = _state_for_ids([])
    raw = 'has, a comma\nhas "a quote"\nhas, both "here"\n\nplain'
    rendered = state.sanitize_notes(raw)
    lines = rendered.split("\n")
    assert lines == ["note 1.0, x", 'note 1.1 "q"', 'note 1.2, x "q"', "", "note 1.4"]
    assert grammar.PLACEHOLDER_RE.fullmatch(rendered)


def test_identical_owner_texts_share_same_k():
    state = _state_for_ids([])
    text = "same owner text"
    assert state.sanitize_notes(text) == state.sanitize_notes(text) == "note 1.0"
    assert state.sanitize_notes("different text") == "note 2.0"


def test_unrecognized_vc_prefixed_segment_becomes_placeholder():
    state = _state_for_ids([])
    rendered = state.sanitize_notes("#vc-test: m3 round trip")
    assert grammar.PLACEHOLDER_RE.fullmatch(rendered)
    assert not any(p.fullmatch(rendered) for p in grammar.RETAINED_CLAUSE_RES)
    assert "m3" not in rendered and "round trip" not in rendered


def test_owner_text_followed_by_clause_keeps_clause():
    state = _state_for_ids(["6900000000000000001"])
    fake = state.id_map["6900000000000000001"]
    raw = "my private note #vc-junk: dupe-lower, kept 6900000000000000001"
    rendered = state.sanitize_notes(raw)
    for segment in re.split(r"(?=#vc-)", rendered):
        stripped = segment.strip()
        if stripped:
            assert grammar.is_retained_or_placeholder(stripped)
    assert f"#vc-junk: dupe-lower, kept {fake}" in rendered
    assert "my private note" not in rendered


def test_owner_text_in_clause_form_becomes_placeholder():
    state = _state_for_ids(["6900000000000000001"])
    real = "6900000000000000001"
    cases = [
        f"#vc-review: armor-similar to {real} (private note)",
        "#vc-junk: dupe-lower, kept secret-text",
        "#vc-junk: armor-score 1 < floor 2 (best: my secret, rank 1/2 anything)",
        ("#vc-review: armor-last-archetype (private words), armor-score 1 < floor 2 "
        "(best: melee_primary, rank 1/2 titan helmet)"),
    ]
    for raw in cases:
        rendered = state.sanitize_notes(raw)
        assert grammar.PLACEHOLDER_RE.fullmatch(rendered), (raw, rendered)
        assert not any(p.fullmatch(rendered) for p in grammar.RETAINED_CLAUSE_RES)
        assert real not in rendered


def test_owner_numbers_and_reference_payloads_never_survive():
    state = _state_for_ids(["6900000000000000001", "6900000000000000002"])
    real = "6900000000000000001"

    r1 = state.sanitize_notes(f"#vc-review: armor-similar to {real} (max stat delta 3141592, total 1)")
    assert "max stat delta 0, total 0" in r1
    assert "3141592" not in r1

    r2 = state.sanitize_notes(
        "#vc-review: coverage-dominated by; compare [id …0001]; "
        "curated matches 123456789 vs 1; partner largest coverage gain"
    )
    assert "curated matches 0 vs 0" in r2
    assert "123456789" not in r2

    r3 = state.sanitize_notes(
        "#vc-junk: armor-score 64.2857 < floor 65 (best: melee_primary, rank 7/9 titan helmet)"
    )
    assert "armor-score 0 < floor 0" in r3 and "rank 0/0" in r3
    assert "64.2857" not in r3 and "7/9" not in r3

    r4 = state.sanitize_notes("#vc-junk: dupe-lower; keep [id …0001; my address]; winner lock")
    assert "my address" not in r4

    for rendered in (r1, r2, r3, r4):
        _assert_retained(rendered)


def test_current_format_ref_resolves_and_drops_other_parts():
    state = _state_for_ids(["6900000000000000001"])
    raw = (
        "#vc-junk: dupe-lower; keep [id …0001; location Vault; Tier 5; MW10; "
        "crafted lv7; roll A / B]; winner lock"
    )
    rendered = state.sanitize_notes(raw)
    for leaked in ("location", "Tier 5", "MW10", "crafted lv7", "roll A"):
        assert leaked not in rendered
    _assert_retained(rendered)


def test_ambiguous_short_id_token_gets_fresh_fake_no_digest():
    # Two ids sharing the same 4-digit suffix: the token cannot resolve uniquely.
    state = _state_for_ids(["6900000000000010001", "6900000000000020001"])
    rendered = state.sanitize_notes("#vc-junk: dupe-lower; keep [id …0001]; winner lock")
    _assert_retained(rendered)
    assert "~" not in rendered  # no digest is ever kept


def test_non_numeric_short_id_token_becomes_placeholder():
    state = _state_for_ids(["6900000000000000001"])
    rendered = state.sanitize_notes("#vc-junk: dupe-lower; keep [id …AB12]; winner lock")
    assert grammar.PLACEHOLDER_RE.fullmatch(rendered)
    assert not any(p.fullmatch(rendered) for p in grammar.RETAINED_CLAUSE_RES)


def test_loadouts_token_count_preserved_including_prefix_token():
    state = _state_for_ids([])
    raw = "12345:My Loadout,Another Loadout,12345:My Loadout"
    rendered = state.sanitize_loadouts(raw)
    tokens = rendered.split(",")
    assert len(tokens) == 3
    assert tokens[0] == tokens[2] == "Loadout 1"
    assert tokens[1] == "Loadout 2"
    assert grammar.LOADOUTS_RE.fullmatch(rendered)


def test_loadouts_empty_stays_empty():
    state = _state_for_ids([])
    assert state.sanitize_loadouts("") == ""
    assert state.sanitize_loadouts("   ") == "   "


def test_kill_tracker_becomes_zero():
    assert se._sanitize_kill_tracker("255") == "0"
    assert se._sanitize_kill_tracker("") == "0"


def test_fake_id_map_preserves_instance_id_order():
    reals = ["6900000000000099999", "690000000000000005", "69000000000000000123"]
    sorted_reals = sorted(set(reals), key=instance_id_order)
    id_map = se._build_id_map(sorted_reals)
    fakes_by_rank = [id_map[r] for r in sorted_reals]
    assert fakes_by_rank == sorted(fakes_by_rank, key=instance_id_order)


# ---------------------------------------------------------------------------
# Grammar coverage: every one of the 12 families, from the production
# emitters wherever one reaches it (synthetic 19-digit-id copies of existing
# rule fixtures), and handwritten only for the three legacy/migration-only
# families no current emitter produces.
# ---------------------------------------------------------------------------


def test_all_twelve_families_have_emitter_or_handwritten_coverage():
    covered_examples: list[str] = []

    # Family 2 (weapon variant, no tuning suffix).
    df = load_weapons(FIXTURES / "weapons_dupes.csv")
    df, m = _remap_ids(df, base=1)
    decisions = {d.id: d for d in dupes.resolve(df, crafted_level_protect=10)}
    raw = df.loc[df["Id"] == m["3002"], "Notes"].iloc[0]
    state = _state_for_ids(df["Id"].tolist())
    covered_examples.append(state.sanitize_notes(_extract_clause(decisions[m["3002"]], raw)))

    # Family 2 (armor variant, with tuning suffix).
    df = load_armor(FIXTURES / "armor_dupes.csv")
    df, m = _remap_ids(df, base=1)
    decisions = {d.id: d for d in armor_dupes.run(df, crafted_level_protect=10)}
    raw = df.loc[df["Id"] == m["5002"], "Notes"].iloc[0]
    state = _state_for_ids(df["Id"].tolist())
    covered_examples.append(state.sanitize_notes(_extract_clause(decisions[m["5002"]], raw)))

    # Families 5 and 6 (close dominated / similar, current format).
    df = load_armor(FIXTURES / "armor_close.csv")
    df, m = _remap_ids(df, base=1)
    exact_decided = {d.id for d in armor_dupes.run(df, crafted_level_protect=10)}
    cfg = load_config(Path("nonexistent.toml"))
    close_decisions = {
        d.id: d for d in armor_close.run(df[~df["Id"].isin(exact_decided)], cfg)
    }
    state = _state_for_ids(df["Id"].tolist())
    for old_id in ("6002", "6011"):
        raw = df.loc[df["Id"] == m[old_id], "Notes"].iloc[0]
        covered_examples.append(state.sanitize_notes(_extract_clause(close_decisions[m[old_id]], raw)))

    # Families 9, 10, 11 (armor score junk / review / last-archetype).
    armor = load_armor(FIXTURES / "armor.csv")
    armor, m = _remap_ids(armor, base=1)
    score_cfg = load_config(Path("nonexistent.toml"))
    score_cfg["armor"]["top_n_per_slot"] = 2
    score_cfg["armor"]["score_floor"] = 60
    score_cfg["armor"]["favored_set_perks"] = ["Test Set Perk"]
    state = _state_for_ids(armor["Id"].tolist())
    neutral = frozenset((h, a) for h, a in zip(armor["Hash"], armor["Archetype"], strict=True))
    neutral_decisions = {d.id: d for d in armor_rules.run(armor, score_cfg, neutral).decisions}
    for old_id in ("4005", "4006"):
        raw = armor.loc[armor["Id"] == m[old_id], "Notes"].iloc[0]
        covered_examples.append(state.sanitize_notes(_extract_clause(neutral_decisions[m[old_id]], raw)))
    empty_decisions = {d.id: d for d in armor_rules.run(armor, score_cfg, frozenset()).decisions}
    raw = armor.loc[armor["Id"] == m["4004"], "Notes"].iloc[0]
    covered_examples.append(state.sanitize_notes(_extract_clause(empty_decisions[m["4004"]], raw)))

    # Family 12 (ghost).
    gh = load_ghosts(FIXTURES / "ghosts_cleanup.csv")
    gh, m = _remap_ids(gh, base=1)
    decisions = {d.id: d for d in ghost_rules.run(gh)}
    raw = gh.loc[gh["Id"] == m["6001"], "Notes"].iloc[0]
    state = _state_for_ids(gh["Id"].tolist())
    covered_examples.append(state.sanitize_notes(_extract_clause(decisions[m["6001"]], raw)))

    # Family 7 (coverage dominated / uncovered).
    perk_map = {
        "frame": frozenset({1000}), "perk a": frozenset({1}), "perk b": frozenset({2, 20}),
        "perk c": frozenset({3}), "perk d": frozenset({4}), "perk e": frozenset({5}),
        "perk f": frozenset({6}), "bad perk": frozenset({99}),
    }
    wl = parse_wishlist((FIXTURES / "wishlist_coverage.txt").read_text(encoding="utf-8"))
    weapons = load_weapons(FIXTURES / "weapons_coverage.csv")
    weapons, m = _remap_ids(weapons, base=1)
    run_res = weapons_rules.run(weapons, wl, perk_map, crafted_level_protect=10)
    decisions = {d.id: d for d in run_res.decisions}
    state = _state_for_ids(weapons["Id"].tolist())
    for old_id in ("10011", "10051"):
        raw = weapons.loc[weapons["Id"] == m[old_id], "Notes"].iloc[0]
        covered_examples.append(state.sanitize_notes(_extract_clause(decisions[m[old_id]], raw)))

    # Family 8 (wishlist-trash), a minimal synthetic pair (junk + locked-review).
    trash_wl = parse_wishlist("dimwishlist:item=-200&perks=\n")
    perk_map2 = {"perk a": frozenset({1})}
    weapons2 = pd.DataFrame([
        _min_weapon_row("6900000000000000301", hash_="200"),
        _min_weapon_row("6900000000000000302", hash_="200", Locked="true"),
    ])
    run_res2 = weapons_rules.run(weapons2, trash_wl, perk_map2, 10)
    decisions2 = {d.id: d for d in run_res2.decisions}
    state = _state_for_ids(weapons2["Id"].tolist())
    for wid in ("6900000000000000301", "6900000000000000302"):
        raw = weapons2.loc[weapons2["Id"] == wid, "Notes"].iloc[0]
        covered_examples.append(state.sanitize_notes(_extract_clause(decisions2[wid], raw)))

    # Families 1, 3, 4: migration-only legacy shapes. No current emitter
    # reaches these — named here per the plan's handwritten-example allowance.
    legacy_state = _state_for_ids(["6900000000000000401"])
    covered_examples.append(
        legacy_state.sanitize_notes("#vc-junk: dupe-lower, kept 6900000000000000401")
    )
    covered_examples.append(
        legacy_state.sanitize_notes(
            "#vc-review: armor-similar to 6900000000000000401 (identical stats)"
        )
    )
    covered_examples.append(
        legacy_state.sanitize_notes("#vc-review: armor-dominated by 6900000000000000401 (+3 total)")
    )

    assert len(covered_examples) >= 15

    matched_families: set[int] = set()
    for rendered in covered_examples:
        _assert_retained(rendered)
        hit = [i for i, p in enumerate(grammar.RETAINED_CLAUSE_RES) if p.fullmatch(rendered)]
        assert len(hit) == 1, (rendered, hit)
        matched_families.add(hit[0])

    assert matched_families == set(range(12))


# ---------------------------------------------------------------------------
# Refusals: each asserts a refusal and that the destination is never created.
# ---------------------------------------------------------------------------


def test_refusal_unclassified_column(tmp_path):
    header = [*_MIN_WEAPON_HEADER, "Bogus Column"]
    row = _min_weapon_row("6900000000000000001")
    row["Bogus Column"] = ""
    snap = _min_snapshot(tmp_path, weapon_rows=[row], weapon_header=header)
    with pytest.raises(se.SanitiseError, match="unclassified column"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out" / "snap").exists()


def test_refusal_id_starts_with_marker(tmp_path):
    snap = _min_snapshot(tmp_path, weapon_rows=[_min_weapon_row("1000000000000000099")])
    with pytest.raises(se.SanitiseError, match="marker"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out" / "snap").exists()


def test_refusal_non_decimal_id(tmp_path):
    snap = _min_snapshot(tmp_path, weapon_rows=[_min_weapon_row("690000000000000000X")])
    with pytest.raises(se.SanitiseError, match="all-decimal"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out" / "snap").exists()


def test_refusal_cr_in_notes(tmp_path):
    snap = _min_snapshot(
        tmp_path, weapon_rows=[_min_weapon_row("6900000000000000001", Notes="a\rb")]
    )
    with pytest.raises(se.SanitiseError, match="carriage return"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out" / "snap").exists()


def test_refusal_missing_export_file(tmp_path):
    snap = _min_snapshot(tmp_path, skip=("ghosts",))
    with pytest.raises(se.SanitiseError, match="missing ghosts.csv"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out" / "snap").exists()


def test_refusal_unexpected_file_in_destination(tmp_path):
    snap = _min_snapshot(tmp_path)
    dest = tmp_path / "out" / "snap"
    dest.mkdir(parents=True)
    (dest / "stray.txt").write_text("not ours", encoding="utf-8")
    with pytest.raises(se.SanitiseError, match="unexpected entry"):
        se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    assert [p.name for p in dest.iterdir()] == ["stray.txt"]


# ---------------------------------------------------------------------------
# Planted leaks: for each, show it survives with its check bypassed
# (monkeypatch the check away too, so the write succeeds despite the
# transform bug — proving the check is what catches it), then restore the
# check and show the same transform bug is refused.
# ---------------------------------------------------------------------------


def test_planted_leak_notes_id_left_unmapped_bypass_then_caught(tmp_path, monkeypatch):
    id_a = "6900000000000000001"
    bypass_snap, _, _ = _two_weapon_snapshot(tmp_path / "bypass", f"references {id_a} directly")

    monkeypatch.setattr(se.SanitiserState, "sanitize_notes", lambda self, value: str(value))
    monkeypatch.setattr(se, "_check_l1", lambda *a, **k: None)
    monkeypatch.setattr(se, "_check_l2", lambda *a, **k: None)
    monkeypatch.setattr(se, "_check_l4", lambda *a, **k: None)
    monkeypatch.setattr(se, "_check_l5", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert id_a in leaked  # the leak really would have survived with these checks off

    monkeypatch.undo()
    caught_snap, _, _ = _two_weapon_snapshot(tmp_path / "caught", f"references {id_a} directly")
    monkeypatch.setattr(se.SanitiserState, "sanitize_notes", lambda self, value: str(value))
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_id_map_returns_raw_id_bypass_then_caught(tmp_path, monkeypatch):
    id_a = "6900000000000000001"
    bypass_snap, _, _ = _two_weapon_snapshot(tmp_path / "bypass", "")
    real_build = se._build_id_map

    def bad_build(sorted_ids):
        mapping = real_build(sorted_ids)
        mapping[id_a] = id_a  # "the id map returns a raw id for this row"
        return mapping

    monkeypatch.setattr(se, "_build_id_map", bad_build)
    monkeypatch.setattr(se, "_check_l1", lambda *a, **k: None)
    monkeypatch.setattr(se, "_check_l3", lambda *a, **k: None)
    monkeypatch.setattr(se, "_check_l4", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert f'"{id_a}"' in leaked

    monkeypatch.undo()
    caught_snap, _, _ = _two_weapon_snapshot(tmp_path / "caught", "")
    monkeypatch.setattr(se, "_build_id_map", bad_build)
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_notes_returns_owner_text_bypass_then_caught(tmp_path, monkeypatch):
    secret = "my secret diary entry"
    bypass_snap = _min_snapshot(tmp_path / "bypass", weapon_rows=[_min_weapon_row("6900000000000000001", Notes=secret)])

    monkeypatch.setattr(se.SanitiserState, "render_placeholder", lambda self, body: body)
    monkeypatch.setattr(se, "_check_l5", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert secret in leaked

    monkeypatch.undo()
    caught_snap = _min_snapshot(tmp_path / "caught", weapon_rows=[_min_weapon_row("6900000000000000001", Notes=secret)])
    monkeypatch.setattr(se.SanitiserState, "render_placeholder", lambda self, body: body)
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_notes_keeps_clause_shaped_owner_note_bypass_then_caught(tmp_path, monkeypatch):
    id_a = "6900000000000000001"
    owner_note = f"#vc-review: armor-similar to {id_a} (private note)"
    bypass_snap = _min_snapshot(tmp_path / "bypass", weapon_rows=[_min_weapon_row(id_a, Notes=owner_note)])

    def fake_recognise(body, resolve_ref):
        return body if body.startswith("#vc-") else None

    monkeypatch.setattr(se, "recognise_and_canonicalise", fake_recognise)
    monkeypatch.setattr(se, "_check_l5", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert "private note" in leaked

    monkeypatch.undo()
    caught_snap = _min_snapshot(tmp_path / "caught", weapon_rows=[_min_weapon_row(id_a, Notes=owner_note)])
    monkeypatch.setattr(se, "recognise_and_canonicalise", fake_recognise)
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_notes_copies_numeric_payload_bypass_then_caught(tmp_path, monkeypatch):
    id_a = "6900000000000000001"
    owner_clause = f"#vc-review: armor-similar to {id_a} (max stat delta 3141592, total 1)"
    bypass_snap = _min_snapshot(tmp_path / "bypass", weapon_rows=[_min_weapon_row(id_a, Notes=owner_clause)])

    def fake_recognise(body, resolve_ref):
        # Recognises the family but "forgets" to zero the numeric slots —
        # the id substitution has already happened by the time this runs.
        return body if body.startswith("#vc-") else None

    monkeypatch.setattr(se, "recognise_and_canonicalise", fake_recognise)
    monkeypatch.setattr(se, "_check_l5", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert "3141592" in leaked

    monkeypatch.undo()
    caught_snap = _min_snapshot(tmp_path / "caught", weapon_rows=[_min_weapon_row(id_a, Notes=owner_clause)])
    monkeypatch.setattr(se, "recognise_and_canonicalise", fake_recognise)
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_loadouts_returns_input_bypass_then_caught(tmp_path, monkeypatch):
    secret_loadout = "12345:My Secret Loadout"
    bypass_snap = _min_snapshot(
        tmp_path / "bypass", weapon_rows=[_min_weapon_row("6900000000000000001", Loadouts=secret_loadout)]
    )

    monkeypatch.setattr(se.SanitiserState, "sanitize_loadouts", lambda self, value: str(value))
    monkeypatch.setattr(se, "_check_l6", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert secret_loadout in leaked

    monkeypatch.undo()
    caught_snap = _min_snapshot(
        tmp_path / "caught", weapon_rows=[_min_weapon_row("6900000000000000001", Loadouts=secret_loadout)]
    )
    monkeypatch.setattr(se.SanitiserState, "sanitize_loadouts", lambda self, value: str(value))
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_kill_tracker_left_unchanged_bypass_then_caught(tmp_path, monkeypatch):
    bypass_snap = _min_snapshot(
        tmp_path / "bypass", weapon_rows=[_min_weapon_row("6900000000000000001", **{"Kill Tracker": "255"})]
    )

    monkeypatch.setattr(se, "_sanitize_kill_tracker", lambda value: str(value))
    monkeypatch.setattr(se, "_check_l7", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    leaked = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    assert "255" in leaked

    monkeypatch.undo()
    caught_snap = _min_snapshot(
        tmp_path / "caught", weapon_rows=[_min_weapon_row("6900000000000000001", **{"Kill Tracker": "255"})]
    )
    monkeypatch.setattr(se, "_sanitize_kill_tracker", lambda value: str(value))
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


def test_planted_leak_wrong_reference_fake_bypass_then_caught(tmp_path, monkeypatch):
    id_a, id_b = "6900000000000000001", "6900000000000000002"
    notes_a = f"#vc-junk: dupe-lower; keep [id …{id_b[-4:]}]; winner lock"
    bypass_snap = _min_snapshot(
        tmp_path / "bypass",
        weapon_rows=[_min_weapon_row(id_a, Notes=notes_a), _min_weapon_row(id_b)],
    )

    def wrong_resolve(self, token):
        # Always resolves to the *first* fake by rank, ignoring the token.
        first_real = min(self.id_map, key=instance_id_order)
        fake = self.id_map[first_real]
        return f"…{fake[-4:]}"

    monkeypatch.setattr(se.SanitiserState, "resolve_ref_token", wrong_resolve)
    monkeypatch.setattr(se, "_check_l9", lambda *a, **k: None)
    se.sanitise(bypass_snap, tmp_path / "out_bypass", CONFIG, True, "2026-09-27")
    staged = (tmp_path / "out_bypass" / "snap" / "weapons.csv").read_text(encoding="utf-8")
    # id_a is first by rank, so the wrong resolver always points back at it —
    # the row referencing id_b ends up (wrongly) pointing at id_a's own fake.
    assert "keep [id …" in staged

    monkeypatch.undo()
    caught_snap = _min_snapshot(
        tmp_path / "caught",
        weapon_rows=[_min_weapon_row(id_a, Notes=notes_a), _min_weapon_row(id_b)],
    )
    monkeypatch.setattr(se.SanitiserState, "resolve_ref_token", wrong_resolve)
    with pytest.raises(se.SanitiseError):
        se.sanitise(caught_snap, tmp_path / "out_caught", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_caught" / "snap").exists()


# ---------------------------------------------------------------------------
# Parity mapping-error test (acceptance criterion 3).
# ---------------------------------------------------------------------------


def test_parity_reversed_tie_break_mapping_is_refused_correct_map_passes(tmp_path, monkeypatch):
    # armor_dupes.csv's "Tie Plate" pair (5021/5022) is decided by
    # "deterministic id tie-break": 5021 survives because it has the lower
    # instance id. Swapping their fakes' rank order flips the survivor.
    snap, _, amap, _ = _build_snapshot(tmp_path / "reversed")
    lower_id, higher_id = amap["5021"], amap["5022"]
    real_build = se._build_id_map

    def swapped(sorted_ids):
        mapping = real_build(sorted_ids)
        mapping[lower_id], mapping[higher_id] = mapping[higher_id], mapping[lower_id]
        return mapping

    monkeypatch.setattr(se, "_build_id_map", swapped)
    with pytest.raises(se.SanitiseError, match="parity"):
        se.sanitise(snap, tmp_path / "out_reversed", CONFIG, True, "2026-09-27")
    assert not (tmp_path / "out_reversed" / "snap").exists()

    monkeypatch.undo()
    good_snap, *_ = _build_snapshot(tmp_path / "correct")
    se.sanitise(good_snap, tmp_path / "out_correct", CONFIG, True, "2026-09-27")
    assert (tmp_path / "out_correct" / "snap" / "provenance.json").exists()


# ---------------------------------------------------------------------------
# Parity wrong-reference tests (PR #183 review): unit tests of the
# comparator directly, on synthetic snapshot-decision pairs. <SID>
# normalisation in 3(c) would consider these equal; only 3(d) can catch them.
# ---------------------------------------------------------------------------


def _decision_dict(kept_id: str, note: str, explanation: dict | None = None) -> dict:
    return {
        "id": "x", "kind": "armor", "hash": "1", "name": "N", "location": "Vault",
        "guardian_class": "Titan", "action": "junk", "tag": "junk",
        "note": note, "kept_id": kept_id, "reason": "armor-exact-dupe",
        "original_tag": "", "original_notes": "", "protection_level": None,
        "protection_reason": "", "locked": False, "equipped": False, "in_loadout": False,
        "candidate_tuning_mod_slot": None, "selected_tuning_mod_slot": None,
        "explanation": explanation,
    }


def test_parity_wrong_reference_id_suffix_detected():
    state = _state_for_ids(["6900000000000000001", "6900000000000000002"])
    kept_real, other_real = "6900000000000000001", "6900000000000000002"
    kept_fake, other_fake = state.id_map[kept_real], state.id_map[other_real]

    raw_d = _decision_dict(
        kept_real, f"#vc-junk: armor-exact-dupe; keep [id …{kept_real[-4:]}]; winner higher Power"
    )
    staged_correct = _decision_dict(
        kept_fake, f"#vc-junk: armor-exact-dupe; keep [id …{kept_fake[-4:]}]; winner higher Power"
    )
    staged_wrong = _decision_dict(
        kept_fake, f"#vc-junk: armor-exact-dupe; keep [id …{other_fake[-4:]}]; winner higher Power"
    )

    assert se._compare_decision(raw_d, staged_correct, state) is False
    assert se._compare_decision(raw_d, staged_wrong, state) is True


def test_parity_wrong_reference_explanation_copy_detected():
    state = _state_for_ids(["6900000000000000001", "6900000000000000002"])
    kept_real, other_real = "6900000000000000001", "6900000000000000002"
    kept_fake, other_fake = state.id_map[kept_real], state.id_map[other_real]
    note = f"#vc-junk: armor-exact-dupe; keep [id …{kept_real[-4:]}]; winner higher Power"
    staged_note = f"#vc-junk: armor-exact-dupe; keep [id …{kept_fake[-4:]}]; winner higher Power"

    def expl(token_suffix_source: str) -> dict:
        return {
            "label": "L", "why": "W",
            "keep_instead": f"copy …{token_suffix_source[-4:]} in the Vault",
            "gives_up": "G", "caveats": (),
        }

    raw_d = _decision_dict(kept_real, note, expl(kept_real))
    staged_correct = _decision_dict(kept_fake, staged_note, expl(kept_fake))
    staged_wrong = _decision_dict(kept_fake, staged_note, expl(other_fake))

    assert se._compare_decision(raw_d, staged_correct, state) is False
    assert se._compare_decision(raw_d, staged_wrong, state) is True


# ---------------------------------------------------------------------------
# F: format (git diff --check equivalent).
# ---------------------------------------------------------------------------


def test_format_trailing_whitespace_refused(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_bytes(b"a,b\n1,2 \n")
    with pytest.raises(se.SanitiseError, match="F:"):
        se._check_format(bad)

    good = tmp_path / "good.csv"
    good.write_bytes(b"a,b\n1,2\n")
    se._check_format(good)  # does not raise


# ---------------------------------------------------------------------------
# Byte stability and provenance shape.
# ---------------------------------------------------------------------------


def test_byte_stability_same_run_date_identical_bytes(tmp_path):
    snap1, *_ = _build_snapshot(tmp_path / "run1")
    snap2, *_ = _build_snapshot(tmp_path / "run2")
    se.sanitise(snap1, tmp_path / "out1", CONFIG, True, "2026-09-27")
    se.sanitise(snap2, tmp_path / "out2", CONFIG, True, "2026-09-27")

    dest1 = tmp_path / "out1" / "snap"
    dest2 = tmp_path / "out2" / "snap"
    for name in ("weapons.csv", "armor.csv", "ghosts.csv", "provenance.json"):
        assert (dest1 / name).read_bytes() == (dest2 / name).read_bytes()


def test_provenance_json_shape(tmp_path):
    snap, *_ = _build_snapshot(tmp_path)
    se.sanitise(snap, tmp_path / "out", CONFIG, True, "2026-09-27")
    doc = json.loads((tmp_path / "out" / "snap" / "provenance.json").read_text(encoding="utf-8"))
    assert set(doc) == {"files", "parity_modes", "run_date", "script_version"}
    assert set(doc["files"]) == {"weapons.csv", "armor.csv", "ghosts.csv"}
    for meta in doc["files"].values():
        assert set(meta) == {"raw_sha256", "rows"}
        assert re.fullmatch(r"[0-9a-f]{64}", meta["raw_sha256"])
        assert isinstance(meta["rows"], int)
    assert doc["parity_modes"] == ["no-wishlists"]
    assert doc["run_date"] == "2026-09-27"
    assert doc["script_version"] == 1
