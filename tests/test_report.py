import csv
from pathlib import Path

import pytest

from vault_cleaner.parse import load_weapons
from vault_cleaner.report import write_import_csv

FIXTURE = Path(__file__).parent / "fixtures" / "weapons.csv"


def test_output_has_dim_import_columns(tmp_path):
    out = tmp_path / "out.csv"
    write_import_csv(
        [{"Id": "1000000000000000001", "Hash": "111111", "Tag": "junk", "Notes": "#vc-junk: test"}],
        out,
    )
    with out.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["Id", "Hash", "Tag", "Notes"]
    assert rows[0]["Tag"] == "junk"
    assert rows[0]["Notes"] == "#vc-junk: test"


def test_ids_are_rewrapped_in_dim_style_quotes(tmp_path):
    out = tmp_path / "out.csv"
    write_import_csv([{"Id": "1000000000000000001", "Hash": "111111", "Tag": "junk", "Notes": ""}], out)
    raw = out.read_text()
    # Literal quotes around the id, doubled per CSV escaping — exactly how DIM exports it.
    assert '"""1000000000000000001"""' in raw


def test_invalid_tag_rejected(tmp_path):
    with pytest.raises(ValueError, match="invalid DIM tag"):
        write_import_csv([{"Id": "1", "Hash": "2", "Tag": "trash", "Notes": ""}], tmp_path / "out.csv")


def test_round_trip_export_to_import(tmp_path):
    weapons = load_weapons(FIXTURE)
    rows = [
        {"Id": r["Id"], "Hash": r["Hash"], "Tag": "junk", "Notes": "#vc-junk: round trip"}
        for _, r in weapons.iterrows()
    ]
    out = tmp_path / "out.csv"
    assert write_import_csv(rows, out) == 3
    with out.open(newline="") as f:
        read_back = list(csv.DictReader(f))
    # csv parsing strips one layer of quoting; the remaining literal quotes are DIM's spreadsheet armor
    assert [r["Id"] for r in read_back] == [
        '"1000000000000000001"',
        '"1000000000000000002"',
        '"1000000000000000003"',
    ]
    assert [r["Hash"] for r in read_back] == ["111111", "111111", "222222"]
