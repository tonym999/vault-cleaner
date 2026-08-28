import csv
import io
from pathlib import Path

import pandas as pd
import pytest

from vault_cleaner.parse import (
    ExportDecodeError,
    SchemaError,
    load_armor,
    load_armor_bytes,
    load_ghosts,
    load_ghosts_bytes,
    load_weapons,
    load_weapons_bytes,
)

FIXTURE = Path(__file__).parent / "fixtures" / "weapons.csv"
GHOST_FIXTURE = Path(__file__).parent / "fixtures" / "ghosts.csv"
ARMOR_FIXTURE = Path(__file__).parent / "fixtures" / "armor.csv"

EXPORT_CASES = [
    ("weapons", FIXTURE, load_weapons, load_weapons_bytes, "weapons export"),
    ("armor", ARMOR_FIXTURE, load_armor, load_armor_bytes, "armor export"),
    ("ghosts", GHOST_FIXTURE, load_ghosts, load_ghosts_bytes, "ghosts export"),
]


def test_load_weapons_by_header_name():
    df = load_weapons(FIXTURE)
    assert len(df) == 3
    assert df.loc[0, "Name"] == "Fake Auto Rifle"
    assert df.loc[2, "Rarity"] == "Exotic"


@pytest.mark.parametrize(
    "prefix",
    [b"", b"\xef\xbb\xbf"],
    ids=["plain-utf8", "utf8-bom"],
)
def test_load_weapons_accepts_utf8_with_or_without_bom(tmp_path, prefix):
    export = tmp_path / "destiny-weapon.csv"
    export.write_bytes(prefix + FIXTURE.read_bytes())

    # pandas strips the UTF-8 BOM; parse.py deliberately delegates that decoding.
    df = load_weapons(export)

    pd.testing.assert_frame_equal(df, load_weapons(FIXTURE))


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


@pytest.mark.parametrize(
    "kind,fixture,path_loader,byte_loader,label",
    EXPORT_CASES,
    ids=[case[0] for case in EXPORT_CASES],
)
@pytest.mark.parametrize("prefix", [b"", b"\xef\xbb\xbf"], ids=["plain-utf8", "utf8-bom"])
def test_byte_loaders_match_path_loaders_for_plain_and_bom_exports(
    tmp_path, kind, fixture, path_loader, byte_loader, label, prefix
):
    content = prefix + fixture.read_bytes()
    path = tmp_path / f"{kind}.csv"
    path.write_bytes(content)

    expected = path_loader(path)
    actual = byte_loader(content)
    pd.testing.assert_frame_equal(actual, expected)


def _rewrite_csv(content, mutate):
    rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))
    mutate(rows)
    output = io.StringIO(newline="")
    csv.writer(output, lineterminator="\n").writerows(rows)
    return output.getvalue().encode("utf-8")


def _drop_column(column):
    def mutate(rows):
        index = rows[0].index(column)
        for row in rows:
            row.pop(index)

    return mutate


def _duplicate_first_item():
    def mutate(rows):
        rows[2:] = [rows[1], rows[1]]

    return mutate


def _set_first_value(column, value):
    def mutate(rows):
        rows[1][rows[0].index(column)] = value

    return mutate


INVALID_EXPORT_CASES = [
    ("weapons", FIXTURE, load_weapons, load_weapons_bytes, "weapons export", _drop_column("Notes")),
    ("weapons-crafted", FIXTURE, load_weapons, load_weapons_bytes, "weapons export", _drop_column("Crafted")),
    ("weapons-crafted-level", FIXTURE, load_weapons, load_weapons_bytes, "weapons export", _drop_column("Crafted Level")),
    ("weapons-unknown-crafted", FIXTURE, load_weapons, load_weapons_bytes, "weapons export", _set_first_value("Crafted", "true")),
    ("armor", ARMOR_FIXTURE, load_armor, load_armor_bytes, "armor export", _drop_column("Notes")),
    ("ghosts", GHOST_FIXTURE, load_ghosts, load_ghosts_bytes, "ghosts export", _drop_column("Notes")),
    ("weapons-duplicate", FIXTURE, load_weapons, load_weapons_bytes, "weapons export", _duplicate_first_item()),
    ("armor-duplicate", ARMOR_FIXTURE, load_armor, load_armor_bytes, "armor export", _duplicate_first_item()),
    ("ghosts-duplicate", GHOST_FIXTURE, load_ghosts, load_ghosts_bytes, "ghosts export", _duplicate_first_item()),
    (
        "armor-stat",
        ARMOR_FIXTURE,
        load_armor,
        load_armor_bytes,
        "armor export",
        _set_first_value("Melee (Base)", ""),
    ),
    (
        "armor-masterwork",
        ARMOR_FIXTURE,
        load_armor,
        load_armor_bytes,
        "armor export",
        _set_first_value("Masterwork Tier", "abc"),
    ),
    (
        "armor-power",
        ARMOR_FIXTURE,
        load_armor,
        load_armor_bytes,
        "armor export",
        _set_first_value("Power", "-5"),
    ),
]


@pytest.mark.parametrize(
    "kind,fixture,path_loader,byte_loader,label,mutate",
    INVALID_EXPORT_CASES,
    ids=[case[0] for case in INVALID_EXPORT_CASES],
)
def test_byte_and_path_rejections_have_matching_schema_errors(
    tmp_path, kind, fixture, path_loader, byte_loader, label, mutate
):
    content = _rewrite_csv(fixture.read_bytes(), mutate)
    path = tmp_path / f"{kind}.csv"
    path.write_bytes(content)

    with pytest.raises(SchemaError) as path_error:
        path_loader(path)
    with pytest.raises(SchemaError) as byte_error:
        byte_loader(content)

    assert type(byte_error.value) is type(path_error.value)
    assert str(byte_error.value) == str(path_error.value).replace(str(path), label, 1)
    assert label in str(byte_error.value)
    assert str(tmp_path) not in str(byte_error.value)


@pytest.mark.parametrize(
    "label,byte_loader",
    [(case[4], case[3]) for case in EXPORT_CASES],
    ids=[case[0] for case in EXPORT_CASES],
)
def test_byte_loaders_reject_malformed_utf8(label, byte_loader):
    with pytest.raises(ExportDecodeError) as error:
        byte_loader(b"\xff,not,utf8\n")

    assert not isinstance(error.value, UnicodeDecodeError)
    assert str(error.value) == f"{label}: invalid UTF-8"
