from pathlib import Path

import pytest
from test_review import build_report, manifest_payload, proposals, write_manifest

from vault_cleaner import cli

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = str(FIXTURES / "weapons_dupes.csv")
ARMOR = str(FIXTURES / "armor.csv")
GHOSTS = str(FIXTURES / "ghosts_cleanup.csv")


def _combined(command: str, tmp_path: Path, *extra: str) -> list[str]:
    return [
        command,
        "--weapons",
        WEAPONS,
        "--armor",
        ARMOR,
        "--ghosts",
        GHOSTS,
        "--no-wishlists",
        "--config",
        "nonexistent.toml",
        "--output",
        str(tmp_path / "output.csv"),
        *extra,
    ]


@pytest.mark.parametrize(
    "args",
    [
        ["roundtrip", "--input", WEAPONS, "--item", "Dupe Rifle"],
        ["dupes", "--input", WEAPONS, "--no-wishlists"],
        ["armor", "--input", ARMOR],
        ["ghosts", "--input", GHOSTS],
    ],
    ids=["roundtrip", "dupes", "armor", "ghosts"],
)
def test_single_export_write_failures_are_clean_errors(
    args, tmp_path, monkeypatch, capsys
):
    def fail_write(rows, output):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(cli, "write_import_csv", fail_write)

    rc = cli.main([
        *args,
        "--config",
        "nonexistent.toml",
        "--output",
        str(tmp_path / "output.csv"),
        "--write",
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "error: CSV not written" in captured.err
    assert "read-only filesystem" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("command", ["report", "review"])
def test_combined_csv_write_failures_are_clean_errors(
    command, tmp_path, monkeypatch, capsys
):
    def fail_write(rows, output):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(cli, "write_import_csv", fail_write)

    rc = cli.main(_combined(command, tmp_path, "--write"))

    captured = capsys.readouterr()
    assert rc == 1
    assert "error:" in captured.err
    assert "CSV not written" in captured.err
    assert "read-only filesystem" in captured.err
    assert "Traceback" not in captured.err
    if command == "review":
        assert "nothing written" in captured.err


def test_review_reports_when_overrides_were_saved_but_csv_was_not(
    tmp_path, monkeypatch, capsys
):
    run = build_report()
    manifest = write_manifest(
        tmp_path,
        manifest_payload(run, [proposals(run)[0].id]),
    )

    def fail_write(rows, output):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(cli, "write_import_csv", fail_write)
    overrides = tmp_path / "overrides.json"
    args = _combined(
        "review",
        tmp_path,
        "--overrides",
        str(overrides),
        "--manifest",
        str(manifest),
        "--write",
    )

    assert cli.main(args) == 1

    captured = capsys.readouterr()
    assert overrides.exists()
    assert f"overrides saved to {overrides}, but CSV not written" in captured.err
    assert "read-only filesystem" in captured.err
    assert "Traceback" not in captured.err


def test_review_override_write_failure_says_nothing_was_written(
    tmp_path, monkeypatch, capsys
):
    run = build_report()
    manifest = write_manifest(
        tmp_path,
        manifest_payload(run, [proposals(run)[0].id]),
    )

    def fail_save(store, path):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(cli, "save_overrides", fail_save)
    output = tmp_path / "output.csv"
    args = _combined(
        "review",
        tmp_path,
        "--overrides",
        str(tmp_path / "overrides.json"),
        "--manifest",
        str(manifest),
        "--write",
    )

    assert cli.main(args) == 1

    captured = capsys.readouterr()
    assert "error: nothing written — overrides not saved" in captured.err
    assert "read-only filesystem" in captured.err
    assert "Traceback" not in captured.err
    assert not output.exists()


def test_review_html_write_failure_is_a_clean_error(tmp_path, monkeypatch, capsys):
    def fail_write(result, output):
        raise PermissionError("read-only filesystem")

    monkeypatch.setattr(cli, "write_review_html", fail_write)

    rc = cli.main(_combined("review-html", tmp_path, "--write"))

    captured = capsys.readouterr()
    assert rc == 1
    assert "error: review page not written" in captured.err
    assert "read-only filesystem" in captured.err
    assert "Traceback" not in captured.err
