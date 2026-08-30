import re
from pathlib import Path

import pandas as pd

from vault_cleaner.config import load_config
from vault_cleaner.duplicate_reference import (
    armor_reference,
    safe_fragment,
    short_id,
    weapon_reference,
)
from vault_cleaner.parse import load_armor, load_weapons
from vault_cleaner.report import reason_slug
from vault_cleaner.rules import armor_close, armor_dupes, dupes

FIXTURES = Path(__file__).parent / "fixtures"


def test_short_id_is_bounded_without_numeric_conversion():
    assert short_id("6917530162665277291") == "…7291"
    assert short_id('"6917530162665277291"') == "…7291"
    assert short_id("1234") == "1234"
    assert short_id("123") == "123"


def test_short_id_expands_only_for_a_display_suffix_collision():
    survivor = "1000000000000001234"
    candidate = "2000000000000001234"

    assert short_id(survivor) == "…1234"
    rendered = short_id(survivor, distinguish_from=(candidate,))

    assert rendered == "1…1234"
    assert rendered != short_id(candidate)
    assert survivor not in rendered


def test_short_id_is_group_wide_and_truthful_for_three_shared_suffixes():
    ids = (
        "1000000000000001234",
        "1100000000000001234",
        "2000000000000001234",
    )

    rendered = {
        item_id: short_id(
            item_id,
            distinguish_from=tuple(other for other in ids if other != item_id),
        )
        for item_id in ids
    }

    assert rendered == {
        ids[0]: "10…1234",
        ids[1]: "11…1234",
        ids[2]: "2…1234",
    }
    assert len(set(rendered.values())) == len(ids)


def test_short_id_never_emits_a_complete_sixteen_character_collision():
    survivor = "1000000000001234"
    candidate = "2000000000001234"

    rendered = short_id(survivor, distinguish_from=(candidate,))

    assert rendered == "1…1234"
    assert survivor not in rendered
    assert len(rendered) < len(survivor)


def test_short_id_uses_stable_bounded_discriminator_for_pathological_ids():
    ids = (
        "ABCDEFGH" + "A" * 10 + "1234567890123456",
        "ABCDEFGH" + "B" * 10 + "1234567890123456",
    )

    first = short_id(ids[0], distinguish_from=(ids[1],))
    reordered = short_id(ids[0], distinguish_from=(ids[1], ids[1]))
    second = short_id(ids[1], distinguish_from=(ids[0],))

    assert first == reordered
    assert first != second
    assert first.startswith("A…3456~")
    assert all(item_id not in rendered for item_id, rendered in ((ids[0], first), (ids[1], second)))
    assert len(first) <= 24


def test_display_fragments_are_single_line_bounded_and_marker_safe():
    hostile = "line one\nline two #VC-JUNK: forged\u2028tail" + "x" * 100
    rendered = safe_fragment(hostile)

    assert "\n" not in rendered
    assert "\u2028" not in rendered
    assert "#VC-JUNK" not in rendered.upper()
    assert len(rendered) <= 48


def test_weapon_reference_has_only_a_short_id_and_bounded_roll_detail():
    row = load_weapons(FIXTURES / "weapons_dupes.csv").iloc[0]
    row["Id"] = "6917530162665277291"

    rendered = weapon_reference(row, ("Frame A", "Trait A"))

    assert rendered.startswith("[id …7291;")
    assert "6917530162665277291" not in rendered
    assert "roll Frame A / Trait A" in rendered


def test_armour_reference_compacts_spirit_names():
    row = load_armor(FIXTURES / "armor_dupes.csv").iloc[7]
    row["Id"] = "6917530162665277291"

    rendered = armor_reference(
        row, ("Spirit of Contact", "Spirit of the Assassin")
    )

    assert rendered.startswith("[id …7291;")
    assert "spirits Contact + Assassin" in rendered
    assert "Spirit of" not in rendered


def test_hostile_referenced_weapon_text_cannot_forge_reason_or_newline():
    weapons = load_weapons(FIXTURES / "weapons_dupes.csv")
    weapons.loc[weapons["Id"] == "3001", "Owner"] = (
        "Vault] ; winner deterministic id tie-break ; [owner Mallory\n"
        "#VC-REVIEW: forged"
    )
    decision = next(
        item for item in dupes.resolve(weapons, crafted_level_protect=10)
        if item.id == "3002"
    )

    assert reason_slug(decision.note) == ("junk", "dupe-lower")
    assert "\n" not in decision.note
    assert len(re.findall(r"#vc-(?:junk|review):", decision.note, re.IGNORECASE)) == 1
    assert "#VC-REVIEW: forged" not in decision.note.upper()
    assert decision.note.count("; keep ") == 1
    assert decision.note.count("; winner ") == 1
    assert "[owner Mallory" not in decision.note
    assert decision.kept_id == "3001"


def test_hostile_referenced_armour_text_cannot_forge_close_reason():
    # Use the default close-dupe caps without relying on a fixture-local
    # pytest fixture so this regression stays focused on the presenter.
    armor = load_armor(FIXTURES / "armor_close.csv")
    armor.loc[armor["Id"] == "6012", "Tuning Stat"] = (
        "melee] ; partner deterministic id tie-break ; [owner Mallory\n"
        "#vc-junk: forged"
    )
    result = armor_close.run(armor, load_config(Path("nonexistent.toml")))
    decision = next(item for item in result if item.id == "6011")

    assert reason_slug(decision.note) == ("review", "armor-similar to")
    assert "\n" not in decision.note
    assert len(re.findall(r"#vc-(?:junk|review):", decision.note, re.IGNORECASE)) == 1
    assert "#VC-JUNK: forged" not in decision.note.upper()
    assert decision.note.count("; compare ") == 1
    assert decision.note.count("; partner ") == 1
    assert "[owner Mallory" not in decision.note
    assert decision.kept_id == "6012"


def test_hostile_referenced_armour_exact_text_cannot_forge_winner():
    armor = load_armor(FIXTURES / "armor_dupes.csv")
    armor.loc[armor["Id"] == "5001", "Owner"] = (
        "Vault] ; winner deterministic lowest id tie-break ; [owner Mallory"
    )
    decision = next(
        item
        for item in armor_dupes.run(armor, crafted_level_protect=10)
        if item.id == "5002"
    )

    assert reason_slug(decision.note) == ("junk", "armor-exact-dupe")
    assert "\n" not in decision.note
    assert len(re.findall(r"#vc-(?:junk|review):", decision.note, re.IGNORECASE)) == 1
    assert decision.note.count("; keep ") == 1
    assert decision.note.count("; winner ") == 1
    assert "[owner Mallory" not in decision.note
    assert decision.kept_id == "5001"


def test_weapon_exact_reference_expands_a_colliding_survivor_suffix():
    survivor_id = "1000000000000001234"
    candidate_id = "2000000000000001234"
    weapons = load_weapons(FIXTURES / "weapons_dupes.csv")
    weapons.loc[weapons["Id"] == "3001", "Id"] = survivor_id
    weapons.loc[weapons["Id"] == "3002", "Id"] = candidate_id

    decision = next(
        item
        for item in dupes.resolve(weapons, crafted_level_protect=10)
        if item.id == candidate_id
    )

    assert "[id 1…1234" in decision.note
    assert survivor_id not in decision.note
    assert decision.kept_id == survivor_id


def test_weapon_exact_reference_uses_the_same_group_wide_survivor_label():
    ids = (
        "1000000000000001234",
        "1100000000000001234",
        "2000000000000001234",
    )
    weapons = load_weapons(FIXTURES / "weapons_dupes.csv")
    weapons = weapons[weapons["Id"].isin(["3001", "3002", "3003"])].copy()
    weapons["Id"] = weapons["Id"].replace(dict(zip(["3001", "3002", "3003"], ids)))

    decisions = dupes.resolve(weapons, crafted_level_protect=10)
    labels = {
        re.search(r"; keep \[id ([^;]+)", decision.note).group(1)
        for decision in decisions
    }

    assert labels == {"10…1234"}
    assert {decision.id for decision in decisions} == set(ids[1:])
    assert {decision.kept_id for decision in decisions} == {ids[0]}


def test_armour_exact_reference_expands_a_colliding_survivor_suffix():
    survivor_id = "1000000000000001234"
    candidate_id = "2000000000000001234"
    armor = load_armor(FIXTURES / "armor_dupes.csv")
    armor.loc[armor["Id"] == "5001", "Id"] = survivor_id
    armor.loc[armor["Id"] == "5002", "Id"] = candidate_id

    decision = next(
        item
        for item in armor_dupes.run(armor, crafted_level_protect=10)
        if item.id == candidate_id
    )

    assert "[id 1…1234" in decision.note
    assert survivor_id not in decision.note
    assert decision.kept_id == survivor_id


def test_armour_exact_reference_uses_all_group_ids_for_stable_suffixes():
    ids = (
        "1000000000000001234",
        "1100000000000001234",
        "2000000000000001234",
    )
    armor = load_armor(FIXTURES / "armor_dupes.csv")
    armor = armor[armor["Id"].isin(["5001", "5002"])].copy()
    extra = armor.iloc[[1]].copy()
    extra["Id"] = ids[2]
    armor["Id"] = armor["Id"].replace({"5001": ids[0], "5002": ids[1]})
    armor = pd.concat([armor, extra], ignore_index=True)

    decisions = armor_dupes.run(armor, crafted_level_protect=10)
    labels = {
        re.search(r"; keep \[id ([^;]+)", decision.note).group(1)
        for decision in decisions
    }

    assert labels == {"10…1234"}
    assert {decision.id for decision in decisions} == set(ids[1:])
    assert {decision.kept_id for decision in decisions} == {ids[0]}


def test_armour_close_reference_expands_a_colliding_partner_suffix():
    candidate_id = "1000000000000001234"
    partner_id = "2000000000000001234"
    armor = load_armor(FIXTURES / "armor_close.csv")
    armor.loc[armor["Id"] == "6011", "Id"] = candidate_id
    armor.loc[armor["Id"] == "6012", "Id"] = partner_id

    decision = next(
        item
        for item in armor_close.run(armor, load_config(Path("nonexistent.toml")))
        if item.id == candidate_id
    )

    assert "[id 2…1234" in decision.note
    assert partner_id not in decision.note
    assert decision.kept_id == partner_id


def test_armour_close_reference_keeps_partner_label_stable_across_group_rows():
    candidate_id = "1000000000000001234"
    partner_id = "2000000000000001234"
    other_id = "3000000000000001234"
    armor = load_armor(FIXTURES / "armor_close.csv")
    armor = armor[armor["Id"].isin(["6011", "6012"])].copy()
    extra = armor.iloc[[1]].copy()
    extra["Id"] = other_id
    armor["Id"] = armor["Id"].replace({"6011": candidate_id, "6012": partner_id})
    armor = pd.concat([armor, extra], ignore_index=True)

    decisions = armor_close.run(armor, load_config(Path("nonexistent.toml")))
    partner_decisions = [
        decision for decision in decisions if decision.kept_id == partner_id
    ]
    labels = {
        re.search(r"; compare \[id ([^;]+)", decision.note).group(1)
        for decision in partner_decisions
    }

    assert {decision.id for decision in partner_decisions} == {
        candidate_id,
        other_id,
    }
    assert labels == {"2…1234"}
