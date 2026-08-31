from pathlib import Path

from vault_cleaner.config import load_config
from vault_cleaner.parse import load_armor, load_weapons
from vault_cleaner.rules import armor, armor_close, armor_dupes, dupes
from vault_cleaner.rules.id_order import instance_id_order

FIXTURES = Path(__file__).parent / "fixtures"


def test_instance_id_order_is_string_based_and_total():
    values = ["01", "1", "000", "0", "18446744073709551616", "z", "a"]
    assert sorted(values, key=instance_id_order) == [
        "0",
        "000",
        "01",
        "1",
        "18446744073709551616",
        "a",
        "z",
    ]
    assert instance_id_order("01") == (0, 1, "1", "01")
    assert instance_id_order("not-a-number") == (1, "not-a-number")


def test_exact_survivor_and_group_order_use_raw_id_tie_break():
    armor_frame = load_armor(FIXTURES / "armor_dupes.csv")
    pair = armor_frame[armor_frame["Hash"] == "720"].copy()
    pair.loc[pair["Id"] == "5021", "Id"] = "01"
    pair.loc[pair["Id"] == "5022", "Id"] = "1"

    forward = armor_dupes.analyse(pair, crafted_level_protect=10)
    reverse = armor_dupes.analyse(pair.iloc[::-1], crafted_level_protect=10)

    assert forward == reverse
    assert forward.groups[0].group_id == "01"
    assert forward.groups[0].preferred_survivor_id == "01"
    assert [member.id for member in forward.groups[0].members] == ["01", "1"]
    assert [decision.id for decision in forward.decisions] == ["1"]
    assert forward.decisions[0].kept_id == "01"


def test_exact_order_handles_arbitrarily_long_decimal_ids_without_int_conversion():
    armor_frame = load_armor(FIXTURES / "armor_dupes.csv")
    pair = armor_frame[armor_frame["Hash"] == "720"].copy()
    low = "18446744073709551616"
    high = "18446744073709551617"
    pair.loc[pair["Id"] == "5021", "Id"] = low
    pair.loc[pair["Id"] == "5022", "Id"] = high

    result = armor_dupes.analyse(pair.iloc[::-1], crafted_level_protect=10)
    assert result.groups[0].group_id == low
    assert result.groups[0].preferred_survivor_id == low
    assert result.decisions[0].id == high
    assert result.decisions[0].kept_id == low


def test_exact_group_order_uses_member_id_not_hash_text():
    armor_frame = load_armor(FIXTURES / "armor_dupes.csv")
    pair = armor_frame[armor_frame["Hash"].isin(["700", "710"])].copy()
    pair.loc[pair["Id"] == "5001", "Id"] = "100"
    pair.loc[pair["Id"] == "5002", "Id"] = "101"
    pair.loc[pair["Id"] == "5011", "Id"] = "2"
    pair.loc[pair["Id"] == "5012", "Id"] = "3"
    pair.loc[pair["Id"] == "5013", "Id"] = "4"

    groups = armor_dupes.analyse(pair, crafted_level_protect=10).groups
    assert [group.group_id for group in groups] == ["2", "100"]


def test_close_partner_order_uses_raw_id_tie_break():
    frame = load_armor(FIXTURES / "armor.csv")
    frame = frame[frame["Id"].isin(["4051", "4052", "4053"])].copy()
    frame.loc[frame["Id"] == "4051", "Id"] = "z"
    frame.loc[frame["Id"] == "4052", "Id"] = "1"
    frame.loc[frame["Id"] == "4053", "Id"] = "01"
    cfg = load_config("nonexistent.toml")

    forward = armor_close.analyse(frame, cfg)
    reverse = armor_close.analyse(frame.iloc[::-1], cfg)
    forward_by_id = {decision.id: decision for decision in forward.decisions}
    reverse_by_id = {decision.id: decision for decision in reverse.decisions}
    assert forward_by_id["z"].kept_id == "01"
    assert {
        (decision.id, decision.kept_id, decision.note)
        for decision in forward.decisions
    } == {
        (decision.id, decision.kept_id, decision.note)
        for decision in reverse.decisions
    }
    assert forward.same_stat_groups == reverse.same_stat_groups
    assert forward_by_id == reverse_by_id


def test_score_rank_order_uses_raw_id_tie_break():
    frame = load_armor(FIXTURES / "armor.csv")
    frame = frame[frame["Id"].isin(["4001", "4002"])].copy()
    frame["Hash"] = "score-tie"
    frame["Archetype"] = ""
    for column in ("Weapons (Base)", "Health (Base)", "Class (Base)",
                   "Grenade (Base)", "Super (Base)", "Melee (Base)"):
        frame[column] = "10"
    frame.loc[frame["Id"] == "4001", "Id"] = "01"
    frame.loc[frame["Id"] == "4002", "Id"] = "1"
    cfg = load_config("nonexistent.toml")
    cfg["armor"]["top_n_per_slot"] = 1
    cfg["armor"]["score_floor"] = 1000

    forward = armor.run(frame, cfg, frozenset({("score-tie", "")}))
    reverse = armor.run(frame.iloc[::-1], cfg, frozenset({("score-tie", "")}))
    assert [evaluation.id for evaluation in forward.evaluations] == ["01", "1"]
    assert [decision.id for decision in forward.decisions] == ["1"]
    assert forward.decisions[0].kept_id == ""
    assert [evaluation.id for evaluation in reverse.evaluations] == ["01", "1"]


def test_weapon_duplicate_order_uses_raw_id_tie_break():
    frame = load_weapons(FIXTURES / "weapons_dupes.csv")
    frame = frame[frame["Id"].isin(["3041", "3042"])].copy()
    frame.loc[frame["Id"] == "3041", "Id"] = "01"
    frame.loc[frame["Id"] == "3042", "Id"] = "1"

    forward = dupes.resolve(frame, crafted_level_protect=10)
    reverse = dupes.resolve(frame.iloc[::-1], crafted_level_protect=10)
    assert [(decision.id, decision.kept_id) for decision in forward] == [("1", "01")]
    assert [(decision.id, decision.kept_id) for decision in reverse] == [("1", "01")]
