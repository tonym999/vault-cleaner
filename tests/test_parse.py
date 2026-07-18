from pathlib import Path

import pytest

from vault_cleaner.parse import SchemaError, load_weapons

FIXTURE = Path(__file__).parent / "fixtures" / "weapons.csv"


def test_load_weapons_by_header_name():
    df = load_weapons(FIXTURE)
    assert len(df) == 3
    assert df.loc[0, "Name"] == "Fake Auto Rifle"
    assert df.loc[2, "Rarity"] == "Exotic"


def test_ids_are_unwrapped_from_dim_quoting():
    df = load_weapons(FIXTURE)
    assert df["Id"].tolist() == [
        "1000000000000000001",
        "1000000000000000002",
        "1000000000000000003",
    ]


def test_empty_cells_are_empty_strings_not_nan():
    df = load_weapons(FIXTURE)
    assert df.loc[0, "Tag"] == ""
    assert df.loc[0, "Notes"] == ""


def test_missing_required_column_fails_loudly(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Name,Hash,Tag\nThing,123,\n")
    with pytest.raises(SchemaError, match="missing expected DIM columns"):
        load_weapons(bad)


def test_duplicate_instance_ids_rejected(tmp_path):
    fixture_lines = FIXTURE.read_text().splitlines()
    bad = tmp_path / "dupes.csv"
    bad.write_text("\n".join([fixture_lines[0], fixture_lines[1], fixture_lines[1]]) + "\n")
    with pytest.raises(SchemaError, match="duplicate instance ids"):
        load_weapons(bad)
