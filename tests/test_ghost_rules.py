from pathlib import Path

import pytest

from vault_cleaner.parse import SchemaError, load_ghosts
from vault_cleaner.rules.ghosts import run

FIXTURE = Path(__file__).parent / "fixtures" / "ghosts_cleanup.csv"


@pytest.fixture
def decisions():
    return {d.id: d for d in run(load_ghosts(FIXTURE))}


def test_unprotected_shells_junked_regardless_of_rarity(decisions):
    # 6001 is Exotic rarity, 6007 Legendary — rarity is cosmetic for ghosts
    assert decisions["6001"].action == "junk"
    assert decisions["6007"].action == "junk"
    assert "#vc-junk: ghost-unprotected-surplus" in decisions["6001"].note


def test_equipped_tagged_shells_untouched(decisions):
    assert "6002" not in decisions  # equipped
    assert "6004" not in decisions  # tag: keep
    assert "6005" not in decisions  # tag: favorite


def test_locked_is_a_keep_signal_not_review(decisions):
    # Per-pass policy: for ghosts the lock IS the keep mechanism — no
    # #vc-review rows, no tag changes
    assert "6003" not in decisions


def test_loadout_membership_protects(decisions):
    assert "6006" not in decisions


def test_note_appends_to_existing_notes(decisions):
    assert decisions["6007"].note == "from the old days #vc-junk: ghost-unprotected-surplus"


def test_only_junk_decisions_emitted(decisions):
    assert all(d.action == "junk" and d.tag == "junk" for d in decisions.values())


def test_missing_loadouts_column_fails_loudly(tmp_path):
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index("Loadouts")
    stripped = [",".join(line.split(",")[:idx] + line.split(",")[idx + 1:]) for line in lines]
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join(stripped) + "\n")
    with pytest.raises(SchemaError, match="missing expected DIM columns"):
        load_ghosts(bad)
