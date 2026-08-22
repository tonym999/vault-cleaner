import csv
from pathlib import Path

import pytest

from vault_cleaner.parse import load_weapons
from vault_cleaner.report import (
    reason_slug,
    render_import_csv,
    summarize,
    write_import_csv,
)
from vault_cleaner.rules.dupes import Decision

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


def test_renderer_matches_writer_bytes_and_preserves_dim_crlf(tmp_path):
    rows = [
        {
            "Id": '"1000000000000000001"',
            "Hash": "111111",
            "Tag": "junk",
            "Notes": "café",
            "Ignored": "not emitted",
        },
        {"Id": "1000000000000000002", "Hash": "222222", "Tag": "keep", "Notes": ""},
    ]

    rendered = render_import_csv(rows)
    out = tmp_path / "out.csv"
    assert write_import_csv(rows, out) == 2
    assert rendered == out.read_bytes()
    assert b"\r\n" in rendered
    assert b"\n" not in rendered.replace(b"\r\n", b"")
    assert b'"""1000000000000000001"""' in rendered
    assert b"Ignored" not in rendered


def test_renderer_and_writer_validate_tags_for_generators(tmp_path):
    def rows():
        yield {"Id": "1", "Hash": "2", "Tag": "junk", "Notes": ""}
        yield {"Id": "3", "Hash": "4", "Tag": "trash", "Notes": ""}

    with pytest.raises(ValueError, match="invalid DIM tag"):
        render_import_csv(rows())
    with pytest.raises(ValueError, match="invalid DIM tag"):
        write_import_csv(rows(), tmp_path / "out.csv")


def test_writer_does_not_partially_write_when_a_later_row_is_invalid(tmp_path):
    def rows():
        yield {"Id": "1", "Hash": "2", "Tag": "keep", "Notes": ""}
        yield {"Id": "3", "Hash": "4", "Tag": "trash", "Notes": ""}

    existing = tmp_path / "existing.csv"
    previous = b"previous good export\r\n"
    existing.write_bytes(previous)
    with pytest.raises(ValueError, match="invalid DIM tag"):
        write_import_csv(rows(), existing)
    assert existing.read_bytes() == previous

    fresh = tmp_path / "not-yet-created" / "nested" / "out.csv"
    with pytest.raises(ValueError, match="invalid DIM tag"):
        write_import_csv(rows(), fresh)
    assert not fresh.exists()
    assert not fresh.parent.exists()


def test_writer_consumes_a_successful_generator_once_and_returns_count(tmp_path):
    expected = [
        {"Id": "1", "Hash": "2", "Tag": "junk", "Notes": ""},
        {"Id": "3", "Hash": "4", "Tag": "keep", "Notes": ""},
    ]
    yielded = []

    def rows():
        for row in expected:
            yielded.append(row)
            yield row

    assert write_import_csv(rows(), tmp_path / "out.csv") == len(expected)
    assert yielded == expected


@pytest.mark.parametrize(
    "note,expected",
    [
        ("old note #vc-junk: dupe-lower, kept 3001", ("junk", "dupe-lower")),
        ("#vc-junk: dupe-tie, kept 3041", ("junk", "dupe-tie")),
        ("#vc-review: dupe-lower (locked), kept 3001", ("review", "dupe-lower")),
        ("#vc-junk: wishlist-trash whole-item", ("junk", "wishlist-trash whole-item")),
        ("#vc-review: wishlist-trash roll (exotic)", ("review", "wishlist-trash roll")),
        ("#vc-junk: armor-score 56.0 < floor 65 (best: melee_primary, rank 26/50 titan gauntlets)",
         ("junk", "armor-score")),
        ("#vc-junk: ghost-unprotected-surplus", ("junk", "ghost-unprotected-surplus")),
        ("no hashtag here", ("unknown", "unknown")),
        # Stacked hashtags from a DIM import/re-export cycle: the LAST
        # (current run's) hashtag must win, not the stale one
        ("#vc-junk: dupe-lower, kept 1 #vc-review: wishlist-trash roll (locked)",
         ("review", "wishlist-trash roll")),
        ("pvp roll #vc-review: dupe-lower (locked), kept 2 #vc-junk: dupe-lower, kept 9",
         ("junk", "dupe-lower")),
    ],
)
def test_reason_slug_from_every_note_shape(note, expected):
    assert reason_slug(note) == expected


def _d(id, name, note, owner="Vault"):
    return Decision(id=id, hash="1", name=name, owner=owner,
                    action="junk" if "#vc-junk" in note else "review",
                    tag="", note=note, kept_id="")


def test_summarize_groups_and_orders():
    sections = [
        ("weapons", [
            _d("1", "Rifle A", "#vc-junk: dupe-lower, kept 9"),
            _d("2", "Rifle B", "#vc-junk: dupe-lower, kept 9"),
            _d("3", "Rifle C", "#vc-review: dupe-lower (locked), kept 9"),
        ]),
        ("armor", [
            _d("4", "Plate", "#vc-junk: armor-score 41.0 < floor 65 (best: melee_primary, rank 9/9 titan chest)"),
        ]),
        ("ghosts", [
            _d("5", "Shell", "#vc-junk: ghost-unprotected-surplus"),
        ]),
    ]
    out = summarize(sections)
    assert out.startswith("would junk 4 item(s) and flag 1 for review")
    # junk groups first, largest first; review last
    assert out.index("JUNK dupe-lower (weapons) — 2 item(s)") < out.index("JUNK armor-score (armor) — 1 item(s)")
    assert out.index("JUNK ghost-unprotected-surplus (ghosts)") < out.index("REVIEW dupe-lower (weapons) — 1 item(s)")
    # per-item lines beneath their group
    assert "  Rifle A (id 1, Vault)" in out
    assert "  Shell (id 5, Vault)" in out


def test_summarize_empty_sections():
    assert summarize([("weapons", [])]).startswith("would junk 0 item(s) and flag 0 for review")


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
