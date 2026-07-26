from pathlib import Path
from shutil import copyfile

import pytest

from vault_cleaner import cli
from vault_cleaner.export_discovery import EXPORT_PATTERNS

FIXTURES = (Path(__file__).parent / "fixtures").resolve()
WEAPONS = FIXTURES / "weapons_dupes.csv"
ARMOR = FIXTURES / "armor.csv"
GHOSTS = FIXTURES / "ghosts_cleanup.csv"


@pytest.mark.parametrize(
    ("argv", "source", "filename", "expected"),
    [
        (
            ["roundtrip", "--item", "Dupe Rifle"],
            WEAPONS,
            "destiny-weapon (1).csv",
            "parsed 17 weapons",
        ),
        (
            [
                "dupes",
                "--no-wishlists",
                "--config",
                "nonexistent.toml",
            ],
            WEAPONS,
            "destiny-weapon(1).csv",
            "parsed 17 weapons",
        ),
        (
            ["armor", "--config", "nonexistent.toml"],
            ARMOR,
            "destiny-armor (2).csv",
            "parsed 15 armor pieces",
        ),
        (
            ["ghosts"],
            GHOSTS,
            "destiny-ghost(3).csv",
            "parsed 7 ghosts",
        ),
    ],
)
def test_single_kind_commands_discover_the_only_numbered_export(
    tmp_path, monkeypatch, capsys, argv, source, filename, expected
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    copyfile(source, input_dir / filename)
    monkeypatch.chdir(tmp_path)

    assert cli.main(argv) == 0

    out = capsys.readouterr().out
    assert expected in out
    assert str(Path("data/in") / filename) in out


def test_combined_command_uses_numbered_export_and_warns_for_missing_kinds(
    tmp_path, monkeypatch, capsys
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    copyfile(WEAPONS, input_dir / "destiny-weapon(7).csv")
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "report",
        "--no-wishlists",
        "--config",
        "nonexistent.toml",
        "--overrides",
        str(tmp_path / "overrides.json"),
    ]) == 0

    captured = capsys.readouterr()
    assert "would junk" in captured.out
    assert "skipping armor" in captured.err
    assert "destiny-armor.csv" in captured.err
    assert "browser-numbered copy" in captured.err
    assert "destiny-armor (1).csv" in captured.err
    assert "skipping ghosts" in captured.err


def test_ambiguous_single_command_refuses_before_loader_is_called(
    tmp_path, monkeypatch, capsys
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    exact = input_dir / "destiny-weapon.csv"
    numbered = input_dir / "destiny-weapon (1).csv"
    exact.write_text("stale", encoding="utf-8")
    numbered.write_text("current", encoding="utf-8")

    def fail_loader(path):
        raise AssertionError(f"loaded ambiguous candidate {path}")

    monkeypatch.setitem(cli.LOADERS, "weapons", fail_loader)
    monkeypatch.chdir(tmp_path)

    assert cli.main(["roundtrip", "--item", "anything"]) == 1

    error = capsys.readouterr().err
    assert exact.name in error
    assert numbered.name in error
    assert "delete or move the stale copies" in error
    assert "this command's explicit input-path option" in error


def test_single_command_explicit_input_bypasses_ambiguous_default_directory(
    tmp_path, monkeypatch, capsys
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    (input_dir / "destiny-weapon.csv").write_text("stale", encoding="utf-8")
    (input_dir / "destiny-weapon (1).csv").write_text("current", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "roundtrip",
        "--input",
        str(WEAPONS),
        "--item",
        "Dupe Rifle",
    ]) == 0
    assert "parsed 17 weapons" in capsys.readouterr().out


def test_combined_ambiguity_is_a_clean_fatal_error(
    tmp_path, monkeypatch, capsys
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    exact = input_dir / "destiny-weapon.csv"
    numbered = input_dir / "destiny-weapon(1).csv"
    exact.write_text("stale", encoding="utf-8")
    numbered.write_text("current", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "report",
        "--armor",
        str(ARMOR),
        "--ghosts",
        str(GHOSTS),
        "--no-wishlists",
        "--config",
        "nonexistent.toml",
    ]) == 1

    error = capsys.readouterr().err
    assert error.startswith("error: multiple weapons exports")
    assert exact.name in error
    assert numbered.name in error
    assert "Traceback" not in error


def test_combined_explicit_inputs_bypass_ambiguous_default_directory(
    tmp_path, monkeypatch, capsys
):
    input_dir = tmp_path / "data" / "in"
    input_dir.mkdir(parents=True)
    (input_dir / "destiny-weapon.csv").write_text("stale", encoding="utf-8")
    (input_dir / "destiny-weapon (1).csv").write_text("current", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "report",
        "--weapons",
        str(WEAPONS),
        "--armor",
        str(ARMOR),
        "--ghosts",
        str(GHOSTS),
        "--no-wishlists",
        "--config",
        "nonexistent.toml",
        "--overrides",
        str(tmp_path / "overrides.json"),
    ]) == 0
    assert "would junk" in capsys.readouterr().out


def test_single_command_zero_candidates_reports_expected_name_and_pattern(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)

    assert cli.main(["ghosts"]) == 1

    error = capsys.readouterr().err
    assert "destiny-ghost.csv" in error
    assert EXPORT_PATTERNS["ghosts"].pattern in error


def test_empty_explicit_input_is_a_clean_error(capsys):
    assert cli.main(["ghosts", "--input", ""]) == 1

    error = capsys.readouterr().err
    assert error.startswith("error: explicit ghosts export path must not be empty")
    assert "Traceback" not in error
