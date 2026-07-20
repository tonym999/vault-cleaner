from pathlib import Path

import pytest

from vault_cleaner.cli import _resolve_armor
from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.parse import SchemaError, load_armor
from vault_cleaner.rules.armor_close import run
from vault_cleaner.rules.armor_dupes import run as run_exact

FIXTURE = Path(__file__).parent / "fixtures" / "armor_close.csv"


@pytest.fixture
def cfg():
    return load_config(Path("nonexistent.toml"))  # pure defaults: caps (5, 12)


def close_decisions(cfg, frame=None):
    """Run the close pass the way the pipeline does: after the exact pass."""
    armor = frame if frame is not None else load_armor(FIXTURE)
    decided = {d.id for d in run_exact(armor, crafted_level_protect=10)}
    return run(armor[~armor["Id"].isin(decided)], cfg)


def by_id(ds):
    return {d.id: d for d in ds}


def test_dominated_piece_reviews_with_surplus(cfg):
    d = by_id(close_decisions(cfg))
    assert d["6002"].action == "review"
    assert d["6002"].tag == ""  # never junk, tag preserved
    assert "#vc-review: armor-dominated by 6001 (+5 total)" in d["6002"].note
    assert "6001" not in d  # the dominator gets no note


def test_mutual_tradeoff_is_similar_both_ways_never_dominated(cfg):
    d = by_id(close_decisions(cfg))
    assert "#vc-review: armor-similar to 6012 (max stat delta 2, total 4)" in d["6011"].note
    assert "#vc-review: armor-similar to 6011 (max stat delta 2, total 4)" in d["6012"].note


def test_different_hash_never_compared(cfg):
    d = by_id(close_decisions(cfg))
    assert "6021" not in d and "6022" not in d


def test_different_tier_never_compared(cfg):
    # same Hash, tiers 4 vs 5, would otherwise dominate
    d = by_id(close_decisions(cfg))
    assert "6023" not in d and "6024" not in d


def test_advice_cites_the_exact_pass_survivor_not_the_junked_twin(cfg):
    # 6031/6032 are exact dupes (6032 junked); 6033 is dominated by the roll.
    # The note must name the surviving 6031 — a junked dominator is false
    # advice — and the junked 6032 must get no close note (one decision each).
    armor = load_armor(FIXTURE)
    exact = by_id(run_exact(armor, crafted_level_protect=10))
    assert exact["6032"].action == "junk"
    d = by_id(close_decisions(cfg))
    assert "6032" not in d
    assert "#vc-review: armor-dominated by 6031" in d["6033"].note


def test_caps_are_inclusive_boundaries(cfg):
    d = by_id(close_decisions(cfg))
    assert "6041" in d and "6042" in d  # per-stat delta exactly 5: similar
    assert "6051" not in d and "6052" not in d  # 6 breaks the per-stat cap
    assert "6061" in d and "6062" in d  # total delta exactly 12: similar
    assert "6071" not in d and "6072" not in d  # 14 breaks the total cap


def test_tuning_twins_name_each_other_and_the_tuning(cfg):
    d = by_id(close_decisions(cfg))
    assert "#vc-review: armor-similar to 6082 (identical stats, tuning melee vs grenade)" in d["6081"].note
    assert "#vc-review: armor-similar to 6081 (identical stats, tuning grenade vs melee)" in d["6082"].note


def test_hard_protected_gets_no_note_but_still_dominates_and_partners(cfg):
    d = by_id(close_decisions(cfg))
    assert "6091" not in d  # equipped: untouched
    assert "#vc-review: armor-dominated by 6091" in d["6092"].note
    assert "#vc-review: armor-similar to 6091" in d["6093"].note


def test_spirit_rolls_are_compatibility_boundaries(cfg):
    # Same spirits: comparable. Different spirits: functionally different
    # exotics, never compared even at identical stats. No visible spirits:
    # unknown roll, compared with nothing.
    d = by_id(close_decisions(cfg))
    assert "#vc-review: armor-similar to 6102" in d["6101"].note
    assert "#vc-review: armor-similar to 6101" in d["6102"].note
    assert "6103" not in d  # identical stats to 6101, different spirits
    assert "6104" not in d  # spiritless: unknown roll
    assert "6105" not in d  # one Spirit of a measured two: truncated identity


def test_one_note_per_piece(cfg):
    ids = [d.id for d in close_decisions(cfg)]
    assert len(ids) == len(set(ids))
    assert all(d.action == "review" for d in close_decisions(cfg))


def test_reversing_the_csv_changes_nothing(cfg):
    forward = {(d.id, d.note) for d in close_decisions(cfg)}
    reversed_ = {(d.id, d.note) for d in close_decisions(cfg, load_armor(FIXTURE).iloc[::-1])}
    assert forward == reversed_


def test_tighter_caps_drop_the_wide_pairs(cfg):
    cfg["armor"]["close_dupes"] = {"max_stat_delta": 2, "max_total_delta": 4}
    d = by_id(close_decisions(cfg))
    assert "6011" in d  # delta (2, 4) still in
    assert "6041" not in d and "6042" not in d  # (5, 10) now out


def test_score_pass_never_junks_a_cited_dominator(cfg):
    # "Only kept pieces dominate" (#18): under a strict-but-valid scoring
    # config, 6002's note says 6001 is the better copy — the score pass must
    # not junk 6001 out from under that advice
    cfg["armor"]["top_n_per_slot"] = 0
    cfg["armor"]["score_floor"] = 200
    decisions, _ = _resolve_armor(load_armor(FIXTURE), cfg)
    d = {x.id: x for x in decisions}
    assert "armor-dominated by 6001" in d["6002"].note
    assert "6001" not in d  # shielded from score junking
    # 6121/6122 share a (Hash, Archetype) but are too far apart for the
    # close pass: the last-of-kind guard (#30) spares the better-scoring
    # 6122 as review; 6121 proves score junk still fires
    assert d["6122"].action == "review"
    assert "armor-last-archetype" in d["6122"].note
    assert d["6121"].action == "junk"


def test_missing_tier_column_fails_loudly(tmp_path):
    # The close pass groups on Tier — its disappearance must be a
    # SchemaError at load, not a KeyError mid-pass
    lines = FIXTURE.read_text().splitlines()
    header = lines[0].split(",")
    idx = header.index("Tier")
    stripped = [",".join(cells.split(",")[:idx] + cells.split(",")[idx + 1:]) for cells in lines]
    bad = tmp_path / "bad.csv"
    bad.write_text("\n".join(stripped) + "\n")
    with pytest.raises(SchemaError, match="Tier"):
        load_armor(bad)


def test_close_dupes_config_validated(tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text("[armor.close_dupes]\nmax_stat_delta = -1\nmax_total_delta = 12\n")
    with pytest.raises(ConfigError, match="max_stat_delta"):
        load_config(bad)
    partial = tmp_path / "partial.toml"
    partial.write_text("[armor.close_dupes]\nmax_stat_delta = 3\n")
    with pytest.raises(ConfigError, match="max_total_delta"):
        load_config(partial)
