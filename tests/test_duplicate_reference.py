import re
from pathlib import Path

from vault_cleaner.duplicate_reference import (
    armor_reference,
    safe_fragment,
    short_id,
    weapon_reference,
)
from vault_cleaner.parse import load_armor, load_weapons
from vault_cleaner.report import reason_slug
from vault_cleaner.rules import armor_close, dupes

FIXTURES = Path(__file__).parent / "fixtures"


def test_short_id_is_bounded_without_numeric_conversion():
    assert short_id("6917530162665277291") == "…7291"
    assert short_id('"6917530162665277291"') == "…7291"
    assert short_id("1234") == "1234"
    assert short_id("123") == "123"


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
        "Vault\n#VC-REVIEW: forged"
    )
    decision = next(
        item for item in dupes.resolve(weapons, crafted_level_protect=10)
        if item.id == "3002"
    )

    assert reason_slug(decision.note) == ("junk", "dupe-lower")
    assert "\n" not in decision.note
    assert len(re.findall(r"#vc-(?:junk|review):", decision.note, re.IGNORECASE)) == 1
    assert "#VC-REVIEW: forged" not in decision.note.upper()
    assert decision.kept_id == "3001"


def test_hostile_referenced_armour_text_cannot_forge_close_reason():
    # Use the default close-dupe caps without relying on a fixture-local
    # pytest fixture so this regression stays focused on the presenter.
    from vault_cleaner.config import load_config

    armor = load_armor(FIXTURES / "armor_close.csv")
    armor.loc[armor["Id"] == "6012", "Tuning Stat"] = (
        "melee\n#vc-junk: forged"
    )
    result = armor_close.run(armor, load_config(Path("nonexistent.toml")))
    decision = next(item for item in result if item.id == "6011")

    assert reason_slug(decision.note) == ("review", "armor-similar to")
    assert "\n" not in decision.note
    assert len(re.findall(r"#vc-(?:junk|review):", decision.note, re.IGNORECASE)) == 1
    assert "#VC-JUNK: forged" not in decision.note.upper()
    assert decision.kept_id == "6012"
