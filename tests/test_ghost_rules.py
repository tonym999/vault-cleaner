from pathlib import Path

import pytest

from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.parse import SchemaError, load_ghosts
from vault_cleaner.rules.ghosts import run

FIXTURE = Path(__file__).parent / "fixtures" / "ghosts_cleanup.csv"
EMPTY_FIXTURE = Path(__file__).parent / "fixtures" / "ghosts.csv"  # real-world: rank cells empty


@pytest.fixture
def cfg():
    c = load_config(Path("nonexistent.toml"))
    c["ghosts"]["keep_top_n"] = 3
    return c


def decisions_by_id(cfg):
    return {d.id: d for d in run(load_ghosts(FIXTURE), cfg)}


def test_top_n_by_energy_then_masterwork_survive(cfg):
    d = decisions_by_id(cfg)
    # top 3: Best (10), Second (9), Tie Energy (4/mw9 beats Surplus A 4/mw4)
    assert "5001" not in d and "5002" not in d and "5008" not in d
    assert d["5006"].action == "junk"


def test_exotic_rarity_is_junk_eligible_for_ghosts(cfg):
    # Nearly every shell is Exotic; rarity must not soft-protect here
    d = decisions_by_id(cfg)
    assert d["5007"].action == "junk"
    assert "ghost-surplus" in d["5007"].note


def test_locked_shell_reviews_even_though_exotic(cfg):
    # rails order reports exotic before locked; ghosts must still review locked
    d = decisions_by_id(cfg)
    assert d["5005"].action == "review"
    assert "(locked)" in d["5005"].note


def test_equipped_and_tagged_hard_protected(cfg):
    d = decisions_by_id(cfg)
    assert "5003" not in d  # equipped, rank 8
    assert "5004" not in d  # tagged keep, rank 9


def test_note_carries_energy_and_rank(cfg):
    d = decisions_by_id(cfg)
    assert "energy 4, rank 4/9" in d["5006"].note


def test_keep_top_n_zero_junks_all_unprotected(cfg):
    cfg["ghosts"]["keep_top_n"] = 0
    d = decisions_by_id(cfg)
    assert set(d) == {"5001", "5002", "5005", "5006", "5007", "5008", "5009"}


def test_missing_rank_column_fails_loudly(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index("Energy Capacity")
    stripped = [",".join(line.split(",")[:idx] + line.split(",")[idx + 1:]) for line in lines]
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join(stripped) + "\n")
    with pytest.raises(SchemaError, match="missing expected DIM columns"):
        load_ghosts(bad)


def test_garbage_rank_cell_fails_loudly(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index("Energy Capacity")
    row = lines[1].split(",")
    row[idx] = "oops"
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join([lines[0], ",".join(row)] + lines[2:]) + "\n")
    with pytest.raises(SchemaError, match="non-numeric 'Energy Capacity' value 'oops'"):
        load_ghosts(bad)


def test_empty_rank_cells_are_the_norm_and_load(cfg):
    # Current DIM exports leave energy/masterwork empty on every shell —
    # loads fine, ties at (0,0), and notes must not fabricate a stat ranking
    df = load_ghosts(EMPTY_FIXTURE)
    cfg["ghosts"]["keep_top_n"] = 0
    decisions = run(df, cfg)
    junk = [d for d in decisions if d.action == "junk"]
    assert junk, "expected surplus decisions from the all-empty fixture"
    assert all("no energy/masterwork data" in d.note for d in junk)
    assert all("energy 0" not in d.note for d in junk)


def test_note_with_real_energy_data_keeps_stat_wording(cfg):
    d = decisions_by_id(cfg)
    assert "energy 4, rank 4/9" in d["5006"].note


def test_tied_ranks_deterministic_across_export_order(tmp_path, cfg):
    # All rank cells empty -> everything ties; a reordered export must junk
    # the SAME shells (else repeated runs cumulatively junk-tag everything,
    # since kept shells emit no row to clear a stale tag)
    lines = EMPTY_FIXTURE.read_text().splitlines()
    reordered = tmp_path / "reordered.csv"
    reordered.write_text("\n".join([lines[0]] + list(reversed(lines[1:]))) + "\n")
    cfg["ghosts"]["keep_top_n"] = 1
    junk_a = {d.id for d in run(load_ghosts(EMPTY_FIXTURE), cfg) if d.action == "junk"}
    junk_b = {d.id for d in run(load_ghosts(reordered), cfg) if d.action == "junk"}
    assert junk_a == junk_b
    # newest (highest instance id) shell wins the tie
    assert junk_a == {"2000000000000000001"}


def test_partial_rank_data_reported_accurately():
    import pandas as pd

    def shell(id, energy, mw):
        return {"Id": id, "Hash": "1", "Name": f"S{id}", "Owner": "Vault",
                "Tag": "", "Notes": "", "Rarity": "Exotic", "Locked": "false",
                "Equipped": "false", "Energy Capacity": energy, "Masterwork Tier": mw}

    cfg = load_config(Path("nonexistent.toml"))
    cfg["ghosts"]["keep_top_n"] = 0
    df = pd.DataFrame([shell("1", "", "5"), shell("2", "0", "0"), shell("3", "", "")]).astype(str)
    notes = {d.id: d.note for d in run(df, cfg)}
    assert "masterwork 5" in notes["1"] and "energy 0" not in notes["1"]
    assert "energy 0" in notes["2"] and "no energy" not in notes["2"]
    assert "no energy/masterwork data" in notes["3"]


def test_invalid_keep_top_n_rejected(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[ghosts]\nkeep_top_n = -1\n")
    with pytest.raises(ConfigError, match="keep_top_n"):
        load_config(p)
