from pathlib import Path

import pytest

from vault_cleaner.parse import SchemaError, load_ghosts, load_weapons

FIXTURE = Path(__file__).parent / "fixtures" / "weapons.csv"
GHOST_FIXTURE = Path(__file__).parent / "fixtures" / "ghosts.csv"


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


def test_load_ghosts():
    df = load_ghosts(GHOST_FIXTURE)
    assert len(df) == 2
    assert df["Id"].tolist() == ["2000000000000000001", "2000000000000000002"]
    assert df.loc[1, "Tag"] == "favorite"


def test_ghost_export_has_no_type_column_but_loads():
    # Ghost exports genuinely lack Type — the ghost schema must not demand it.
    df = load_ghosts(GHOST_FIXTURE)
    assert "Type" not in df.columns


def test_weapons_loader_rejects_ghost_export():
    with pytest.raises(SchemaError, match="isn't a weapons export"):
        load_weapons(GHOST_FIXTURE)


def test_duplicate_instance_ids_rejected(tmp_path):
    fixture_lines = FIXTURE.read_text().splitlines()
    bad = tmp_path / "dupes.csv"
    bad.write_text("\n".join([fixture_lines[0], fixture_lines[1], fixture_lines[1]]) + "\n")
    with pytest.raises(SchemaError, match="duplicate instance ids"):
        load_weapons(bad)
