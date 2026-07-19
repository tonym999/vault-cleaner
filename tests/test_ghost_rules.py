from pathlib import Path

import pytest

from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.parse import load_ghosts
from vault_cleaner.rules.ghosts import run

FIXTURE = Path(__file__).parent / "fixtures" / "ghosts_cleanup.csv"


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


def test_invalid_keep_top_n_rejected(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[ghosts]\nkeep_top_n = -1\n")
    with pytest.raises(ConfigError, match="keep_top_n"):
        load_config(p)
