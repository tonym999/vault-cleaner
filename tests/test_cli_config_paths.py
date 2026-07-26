from pathlib import Path
from shutil import copyfile

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
    assert f"parsed 17 weapons from {project / 'exports' / 'destiny-weapon.csv'}" in out


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
