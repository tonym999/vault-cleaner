from pathlib import Path
from shutil import copyfile

import pytest

from vault_cleaner import cli

FIXTURES = Path(__file__).parent / "fixtures"


def _write_config(root: Path, *, input_dir: str = "exports", output_dir: str = "out") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    config = root / "config.toml"
    config.write_text(
        "[paths]\n"
        f'input_dir = "{input_dir}"\n'
        f'output_dir = "{output_dir}"\n',
        encoding="utf-8",
    )
    return config


def _copy_exports(input_dir: Path) -> None:
    input_dir.mkdir(parents=True)
    copyfile(FIXTURES / "weapons_dupes.csv", input_dir / "destiny-weapon.csv")
    copyfile(FIXTURES / "armor.csv", input_dir / "destiny-armor.csv")
    copyfile(FIXTURES / "ghosts_cleanup.csv", input_dir / "destiny-ghost.csv")


def test_report_uses_configured_input_and_output_dirs(tmp_path, capsys):
    project = tmp_path / "project"
    _copy_exports(project / "exports")
    config = _write_config(project)

    assert cli.main([
        "report",
        "--config", str(config),
        "--no-wishlists",
        "--write",
    ]) == 0

    out = capsys.readouterr().out
    target = project / "out" / "dim-import.csv"
    assert "wrote " in out
    assert str(target) in out
    assert target.exists()


def test_missing_nested_config_keeps_cwd_defaults(tmp_path, monkeypatch, capsys):
    project = tmp_path / "project"
    _copy_exports(tmp_path / "data" / "in")
    config = project / "config.toml"
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "report",
        "--config", str(config),
        "--no-wishlists",
        "--write",
    ]) == 0

    out = capsys.readouterr().out
    target = tmp_path / "data" / "out" / "dim-import.csv"
    assert "data/out/dim-import.csv" in out
    assert target.exists()


def test_existing_config_without_paths_bases_defaults_at_config_parent(
    tmp_path, monkeypatch, capsys,
):
    project = tmp_path / "project"
    _copy_exports(project / "data" / "in")
    config = project / "config.toml"
    config.write_text("[armor]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert cli.main([
        "report",
        "--config", str(config),
        "--no-wishlists",
        "--write",
    ]) == 0

    out = capsys.readouterr().out
    target = project / "data" / "out" / "dim-import.csv"
    assert str(target) in out
    assert target.exists()


def test_configured_input_dir_uses_export_discovery(tmp_path, capsys):
    project = tmp_path / "project"
    exports = project / "exports"
    exports.mkdir(parents=True)
    copyfile(FIXTURES / "weapons_dupes.csv", exports / "destiny-weapon (2).csv")
    config = _write_config(project)

    assert cli.main([
        "roundtrip",
        "--config", str(config),
        "--item", "Dupe Rifle",
    ]) == 0

    out = capsys.readouterr().out
    assert f"parsed 18 weapons from {exports / 'destiny-weapon (2).csv'}" in out


def test_configured_input_dir_refuses_ambiguous_exports(tmp_path, capsys):
    project = tmp_path / "project"
    exports = project / "exports"
    exports.mkdir(parents=True)
    (exports / "destiny-weapon.csv").write_text("stale", encoding="utf-8")
    (exports / "destiny-weapon (1).csv").write_text("current", encoding="utf-8")
    copyfile(FIXTURES / "armor.csv", exports / "destiny-armor.csv")
    copyfile(FIXTURES / "ghosts_cleanup.csv", exports / "destiny-ghost.csv")
    config = _write_config(project)

    assert cli.main([
        "report",
        "--config", str(config),
        "--no-wishlists",
    ]) == 1

    error = capsys.readouterr().err
    assert "multiple weapons exports" in error
    assert "destiny-weapon.csv" in error
    assert "destiny-weapon (1).csv" in error


def test_cli_input_path_overrides_configured_input_dir(tmp_path, capsys):
    project = tmp_path / "project"
    config = _write_config(project, input_dir="missing")

    assert cli.main([
        "report",
        "--config", str(config),
        "--weapons", str(FIXTURES / "weapons_dupes.csv"),
        "--armor", str(FIXTURES / "armor.csv"),
        "--ghosts", str(FIXTURES / "ghosts_cleanup.csv"),
        "--no-wishlists",
    ]) == 0

    assert "would junk" in capsys.readouterr().out


def test_roundtrip_accepts_configured_input_dir(tmp_path, capsys):
    project = tmp_path / "project"
    _copy_exports(project / "exports")
    config = _write_config(project)

    assert cli.main([
        "roundtrip",
        "--config", str(config),
        "--item", "Dupe Rifle",
    ]) == 0

    out = capsys.readouterr().out
    assert f"parsed 18 weapons from {project / 'exports' / 'destiny-weapon.csv'}" in out


def test_roundtrip_ignores_unrelated_armor_config_errors(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[armor]\ntop_n_per_slot = -1\n", encoding="utf-8")

    assert cli.main([
        "roundtrip",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "weapons_dupes.csv"),
        "--item", "Dupe Rifle",
    ]) == 0

    assert "parsed 18 weapons" in capsys.readouterr().out


def test_ghosts_accepts_configured_input_dir(tmp_path, capsys):
    project = tmp_path / "project"
    _copy_exports(project / "exports")
    config = _write_config(project)

    assert cli.main([
        "ghosts",
        "--config", str(config),
    ]) == 0

    out = capsys.readouterr().out
    assert f"parsed 7 ghosts from {project / 'exports' / 'destiny-ghost.csv'}" in out


def test_ghosts_ignores_unrelated_armor_config_errors(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[armor]\ntop_n_per_slot = -1\n", encoding="utf-8")

    assert cli.main([
        "ghosts",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "ghosts_cleanup.csv"),
    ]) == 0

    assert "parsed 7 ghosts" in capsys.readouterr().out


@pytest.mark.parametrize("command", ["report", "review"])
def test_combined_command_reads_paths_config_once(command, tmp_path, monkeypatch):
    project = tmp_path / "project"
    _copy_exports(project / "exports")
    config = _write_config(project)
    monkeypatch.chdir(project)
    original = cli.load_paths_config
    calls = 0

    def counted_load_paths_config(path):
        nonlocal calls
        calls += 1
        return original(path)

    monkeypatch.setattr(cli, "load_paths_config", counted_load_paths_config)

    assert cli.main([
        command,
        "--config", str(config),
        "--no-wishlists",
    ]) == 0
    assert calls == 1


def test_roundtrip_rejects_malformed_paths_config(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[paths\ninput_dir = \"exports\"\n", encoding="utf-8")

    assert cli.main([
        "roundtrip",
        "--config", str(bad_config),
        "--item", "Dupe Rifle",
    ]) == 1

    assert "error:" in capsys.readouterr().err


def test_ghosts_rejects_invalid_paths_table(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("paths = true\n", encoding="utf-8")

    assert cli.main([
        "ghosts",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "ghosts_cleanup.csv"),
    ]) == 1

    assert "[paths] must be a table" in capsys.readouterr().err


def test_roundtrip_rejects_non_string_paths_value(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[paths]\noutput_dir = 123\n", encoding="utf-8")

    assert cli.main([
        "roundtrip",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "weapons_dupes.csv"),
        "--item", "Dupe Rifle",
    ]) == 1

    assert "paths.output_dir must be a string" in capsys.readouterr().err


def test_dupes_rejects_non_string_paths_value_cleanly(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[paths]\ninput_dir = 123\n", encoding="utf-8")

    assert cli.main([
        "dupes",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "weapons_dupes.csv"),
        "--no-wishlists",
    ]) == 1

    err = capsys.readouterr().err
    assert "paths.input_dir must be a string" in err
    assert "Traceback" not in err


def test_armor_rejects_non_string_paths_value_cleanly(tmp_path, capsys):
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("[paths]\ninput_dir = 123\n", encoding="utf-8")

    assert cli.main([
        "armor",
        "--config", str(bad_config),
        "--input", str(FIXTURES / "armor.csv"),
    ]) == 1

    err = capsys.readouterr().err
    assert "paths.input_dir must be a string" in err
    assert "Traceback" not in err
