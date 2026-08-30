import re
from pathlib import Path

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
