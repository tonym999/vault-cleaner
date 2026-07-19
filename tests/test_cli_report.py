import csv
from pathlib import Path

from vault_cleaner import cli

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = str(FIXTURES / "weapons_dupes.csv")
ARMOR = str(FIXTURES / "armor.csv")
GHOSTS = str(FIXTURES / "ghosts_cleanup.csv")


def run_report(*extra: str) -> int:
    return cli.main([
        "report", "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml", *extra,
    ])


def test_report_dry_run_over_all_fixtures(capsys):
    assert run_report() == 0
    out = capsys.readouterr().out
    assert out.startswith("would junk")
    assert "JUNK dupe-lower (weapons)" in out
    assert "JUNK ghost-unprotected-surplus (ghosts)" in out
    assert "dry run — pass --write" in out


def test_report_missing_export_skipped_not_fatal(capsys, tmp_path):
    rc = cli.main([
        "report", "--weapons", str(tmp_path / "nope.csv"), "--armor", ARMOR,
        "--ghosts", GHOSTS, "--no-wishlists", "--config", "nonexistent.toml",
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "skipping weapons" in captured.err
    assert "(weapons)" not in captured.out
    assert "JUNK ghost-unprotected-surplus (ghosts)" in captured.out


def test_report_all_exports_missing_errors(capsys, tmp_path):
    rc = cli.main([
        "report", "--weapons", str(tmp_path / "a.csv"), "--armor", str(tmp_path / "b.csv"),
        "--ghosts", str(tmp_path / "c.csv"), "--no-wishlists", "--config", "nonexistent.toml",
    ])
    assert rc == 1
    assert "nothing to report on" in capsys.readouterr().err


def test_report_write_emits_combined_csv(capsys, tmp_path):
    out_csv = tmp_path / "combined.csv"
    assert run_report("--write", "--output", str(out_csv)) == 0
    with out_csv.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == ["Id", "Hash", "Tag", "Notes"]
    # every pass contributed: weapon dupes, armor scores, ghost surplus
    notes = " ".join(r["Notes"] for r in rows)
    assert "dupe-lower" in notes and "armor-score" in notes and "ghost-unprotected-surplus" in notes
    assert f"wrote {len(rows)} row(s)" in capsys.readouterr().out


def test_report_prints_conflict_note(capsys, monkeypatch):
    monkeypatch.setattr(cli, "_resolve_weapons", lambda weapons, cfg, nw: ([], 3, True))
    assert run_report() == 0
    assert "3 weapon(s) matched both keep and trash lists" in capsys.readouterr().out
