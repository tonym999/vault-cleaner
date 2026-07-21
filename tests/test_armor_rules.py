from pathlib import Path

import pytest

from vault_cleaner.config import load_config
from vault_cleaner.parse import ARMOR_STATS, SchemaError, load_armor, load_weapons
from vault_cleaner.rules.armor import base_stats, best_score, run, score_archetype

FIXTURE = Path(__file__).parent / "fixtures" / "armor.csv"


@pytest.fixture
def cfg():
    c = load_config(Path("nonexistent.toml"))  # pure defaults
    # Tuned for the fixture: keep top 2 per slot, floor 60, favor the test
    # set, and add the spike archetype (not a default) to exercise top_stats
    c["armor"]["top_n_per_slot"] = 2
    c["armor"]["score_floor"] = 60
    c["armor"]["favored_set_perks"] = ["Test Set Perk"]
    c["armor"]["archetypes"]["spike"] = {"top_stats": 2}
    return c


def result(cfg, kept_elsewhere=None):
    armor = load_armor(FIXTURE)
    if kept_elsewhere is None:
        # Neutralize the last-of-kind guard (#30): most fixture rows are the
        # sole copy of their (Hash, Archetype), and these tests target the
        # floor/top-N logic. The guard has its own tests below.
        kept_elsewhere = frozenset((h, a) for h, a in zip(armor["Hash"], armor["Archetype"]))
    return run(armor, cfg, kept_elsewhere)


def decisions_by_id(cfg, kept_elsewhere=None):
    return {d.id: d for d in result(cfg, kept_elsewhere).decisions}


def test_load_armor_by_header_and_stat_map():
    df = load_armor(FIXTURE)
    stats = base_stats(df.iloc[0])
    assert stats == {"weapons": 5, "health": 20, "class": 10, "grenade": 5, "super": 5, "melee": 30}
    assert set(stats) == set(ARMOR_STATS)


def test_weapons_loader_rejects_armor_export():
    with pytest.raises(SchemaError, match="isn't a weapons export"):
        load_weapons(FIXTURE)


def test_malformed_stat_cell_fails_loudly(tmp_path):
    # An empty/garbage (Base) cell must not silently score as 0 and junk
    # a good piece — refuse the whole export with the offender named
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    col_idx = header.index('"Melee (Base)"') if '"Melee (Base)"' in header else header.index("Melee (Base)")
    row = lines[1].split(",")
    row[col_idx] = ""
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join([lines[0], ",".join(row)] + lines[2:]) + "\n")
    with pytest.raises(SchemaError, match="non-numeric 'Melee \\(Base\\)'"):
        load_armor(bad)


def test_negative_stat_cell_fails_loudly(tmp_path):
    # Base stats are non-negative; -1 must not quietly lower a score
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    col_idx = header.index("Melee (Base)")
    row = lines[1].split(",")
    row[col_idx] = "-1"
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join([lines[0], ",".join(row)] + lines[2:]) + "\n")
    with pytest.raises(SchemaError, match="non-numeric 'Melee \\(Base\\)' value '-1'"):
        load_armor(bad)


def test_padded_favored_set_perk_still_matches(cfg):
    # " Test Set Perk " in config must match the export's stripped name
    cfg["armor"]["favored_set_perks"] = ["  Test Set Perk  "]
    cfg["armor"]["score_floor"] = 45  # 36 + 10 bonus survives only if matched
    assert "4008" not in decisions_by_id(cfg)


def test_scores_are_on_total_base_scale():
    # Uniform stats: every archetype scores exactly the Total (Base) value
    uniform = {s: 10 for s in ARMOR_STATS}
    assert score_archetype(uniform, {"weights": {"melee": 3.0, "health": 1.0}}) == 60
    assert score_archetype(uniform, {"top_stats": 2}) == 60


def test_spike_archetype_rewards_two_high_stats():
    spiky = {"weapons": 30, "health": 0, "class": 0, "grenade": 30, "super": 0, "melee": 0}
    assert score_archetype(spiky, {"top_stats": 2}) == 180


def test_best_score_picks_max_archetype():
    spiky = {"weapons": 30, "health": 0, "class": 0, "grenade": 30, "super": 0, "melee": 0}
    score, name = best_score(spiky, {"spike": {"top_stats": 2}, "flat": {"weights": {s: 1.0 for s in spiky}}})
    assert (score, name) == (180, "spike")


def test_top_n_survive_and_low_pieces_junked(cfg):
    d = decisions_by_id(cfg)
    assert "4001" not in d and "4002" not in d  # top-2 in slot
    assert d["4004"].action == "junk"
    assert d["4005"].action == "junk"
    assert "armor-score" in d["4005"].note and "< floor 60" in d["4005"].note


def test_above_floor_outside_top_n_untouched(cfg):
    # Decent Plate ranks 3rd (outside top-2) but scores >= floor: left alone
    assert "4003" not in decisions_by_id(cfg)


def test_soft_and_hard_rails_apply(cfg):
    d = decisions_by_id(cfg)
    assert d["4006"].action == "review"
    assert "(locked)" in d["4006"].note
    assert "4007" not in d  # tagged keep — hard rail


def test_set_bonus_rescues_favored_set_piece(cfg):
    # 36 base + 10 bonus = 46: still under floor — but drop the floor and it survives
    d = decisions_by_id(cfg)
    assert d["4008"].action == "junk"
    cfg["armor"]["score_floor"] = 45
    assert "4008" not in decisions_by_id(cfg)
    cfg["armor"]["favored_set_perks"] = []
    assert decisions_by_id(cfg)["4008"].action == "junk"  # bonus gone, floor 45 > 36


def test_small_groups_protected_by_top_n(cfg):
    d = decisions_by_id(cfg)
    assert "4011" not in d and "4012" not in d  # only 2 helmets — both top-N


def test_classes_and_slots_group_independently(cfg):
    # The lone Warlock chest is its own group: top-N keeps it despite bad stats
    assert "4021" not in decisions_by_id(cfg)


def test_exotics_never_scored(cfg):
    assert "4031" not in decisions_by_id(cfg)
    assert result(cfg).scored == 14  # 15 rows minus the exotic


def test_last_of_kind_demoted_to_review(cfg):
    # 4004 is the vault's only copy of its (Hash, Archetype): junking it
    # would foreclose that set/build option with no dupe reasoning (#30)
    d = decisions_by_id(cfg, kept_elsewhere=frozenset())
    assert d["4004"].action == "review"
    assert d["4004"].tag == ""  # existing tag preserved
    assert "#vc-review: armor-last-archetype (no archetype), armor-score" in d["4004"].note


def test_guard_spares_only_the_best_of_a_combo(cfg):
    # Guard Plates A+B share (Hash, Archetype); A scores higher, so A is
    # demoted to review and B still junks. C shares the Hash but not the
    # Archetype — its own combo, so it is spared too.
    d = decisions_by_id(cfg, kept_elsewhere=frozenset())
    assert d["4051"].action == "review"
    assert "armor-last-archetype (no archetype)" in d["4051"].note
    assert d["4052"].action == "junk"
    assert d["4053"].action == "review"
    assert "armor-last-archetype (gunner)" in d["4053"].note


def test_kept_elsewhere_counts_as_combo_survivor(cfg):
    # A review-noted twin outside the score frame means the combo survives:
    # no demotion, both copies junk normally
    d = decisions_by_id(cfg, kept_elsewhere=frozenset({("555001", "")}))
    assert d["4051"].action == "junk"
    assert d["4052"].action == "junk"
    assert d["4053"].action == "review"  # different archetype: still guarded
