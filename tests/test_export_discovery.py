import os
from pathlib import Path
from shutil import copyfile

import pytest

from vault_cleaner import report_run
from vault_cleaner.export_discovery import (
    EXPORT_FILENAMES,
    EXPORT_PATTERNS,
    AmbiguousExportError,
    ExportDiscoveryError,
    MissingExportError,
    discover_export,
    select_export,
)
from vault_cleaner.report_run import NoExportsError, run_report, snapshot_json

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE_EXPORTS = {
    "weapons": FIXTURES / "weapons_dupes.csv",
    "armor": FIXTURES / "armor.csv",
    "ghosts": FIXTURES / "ghosts_cleanup.csv",
}


@pytest.mark.parametrize("kind", sorted(EXPORT_FILENAMES))
def test_exact_expected_name_is_used_when_it_is_the_only_candidate(tmp_path, kind):
    candidate = tmp_path / EXPORT_FILENAMES[kind]
    candidate.write_text("", encoding="utf-8")

    assert discover_export(kind, tmp_path) == candidate


@pytest.mark.parametrize("suffix", ["(1)", " (1)"])
@pytest.mark.parametrize("kind", sorted(EXPORT_FILENAMES))
def test_both_browser_numbering_styles_are_used_when_unambiguous(
    tmp_path, kind, suffix
):
    candidate = tmp_path / f"{Path(EXPORT_FILENAMES[kind]).stem}{suffix}.csv"
    candidate.write_text("", encoding="utf-8")

    assert discover_export(kind, tmp_path) == candidate


def test_lookalike_names_do_not_match(tmp_path):
    expected = tmp_path / "destiny-weapon(12).csv"
    expected.write_text("", encoding="utf-8")
    for name in (
        "destiny-weapon (x).csv",
        "destiny-weapon (1).CSV",
        "destiny-weapon.csv.bak",
        "prefix-destiny-weapon.csv",
        "destiny-weapon (٣).csv",
        "DESTINY-WEAPON.CSV",
    ):
        (tmp_path / name).write_text("", encoding="utf-8")

    assert discover_export("weapons", tmp_path) == expected


def test_matching_directory_is_ignored(tmp_path):
    (tmp_path / "destiny-weapon.csv").mkdir()
    candidate = tmp_path / "destiny-weapon (1).csv"
    candidate.write_text("", encoding="utf-8")

    assert discover_export("weapons", tmp_path) == candidate


def test_zone_identifier_sidecar_is_ignored(tmp_path):
    candidate = tmp_path / "destiny-armor (2).csv"
    candidate.write_text("", encoding="utf-8")
    (tmp_path / "destiny-armor (2).csv:Zone.Identifier").write_text(
        "", encoding="utf-8"
    )

    assert discover_export("armor", tmp_path) == candidate


def test_directory_scan_os_error_is_clean(tmp_path, monkeypatch):
    def deny_access(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "iterdir", deny_access)

    with pytest.raises(
        ExportDiscoveryError,
        match="could not search for weapons exports.*denied",
    ):
        discover_export("weapons", tmp_path)


def test_zero_candidates_names_the_expected_file_and_pattern(tmp_path):
    with pytest.raises(MissingExportError) as raised:
        discover_export("armor", tmp_path)

    message = str(raised.value)
    assert "destiny-armor.csv" in message
    assert EXPORT_PATTERNS["armor"].pattern in message
    assert str(tmp_path) in message
    assert str(tmp_path) not in raised.value.warning_reason
    assert "browser-numbered copy" in raised.value.warning_reason
    assert "destiny-armor (1).csv" in raised.value.warning_reason
    assert EXPORT_PATTERNS["armor"].pattern not in raised.value.warning_reason


def test_ambiguity_lists_every_filename_in_stable_order_with_guidance(tmp_path):
    names = (
        "destiny-weapon.csv",
        "destiny-weapon (2).csv",
        "destiny-weapon(1).csv",
    )
    for name in names:
        (tmp_path / name).write_text("", encoding="utf-8")

    with pytest.raises(AmbiguousExportError) as raised:
        discover_export("weapons", tmp_path)

    assert raised.value.filenames == tuple(sorted(names))
    message = str(raised.value)
    assert all(name in message for name in names)
    assert "delete or move the stale copies" in message
    assert "this command's explicit input-path option" in message


def test_newer_candidate_never_wins(tmp_path):
    exact = tmp_path / "destiny-ghost.csv"
    numbered = tmp_path / "destiny-ghost (1).csv"
    exact.write_text("old", encoding="utf-8")
    numbered.write_text("new", encoding="utf-8")
    os.utime(exact, (1, 1))
    os.utime(numbered, (2, 2))

    with pytest.raises(AmbiguousExportError) as raised:
        discover_export("ghosts", tmp_path)

    assert set(raised.value.filenames) == {exact.name, numbered.name}


def test_explicit_path_bypasses_discovery_entirely(tmp_path, monkeypatch):
    explicit = tmp_path / "chosen.csv"

    def fail_discovery(*args, **kwargs):
        raise AssertionError("explicit paths must not scan the directory")

    monkeypatch.setattr(
        "vault_cleaner.export_discovery.discover_export",
        fail_discovery,
    )
    assert select_export("weapons", explicit, tmp_path / "ambiguous") == explicit


def test_empty_explicit_path_is_rejected_cleanly(tmp_path):
    with pytest.raises(ExportDiscoveryError, match="must not be empty"):
        select_export("ghosts", "", tmp_path)


def test_report_resolves_every_kind_before_reading_any_export(tmp_path, monkeypatch):
    for kind, source in SOURCE_EXPORTS.items():
        copyfile(source, tmp_path / EXPORT_FILENAMES[kind])
    copyfile(
        SOURCE_EXPORTS["ghosts"],
        tmp_path / "destiny-ghost (1).csv",
    )

    def fail_read(path):
        raise AssertionError(f"read {path} before resolving every kind")

    monkeypatch.setattr(report_run, "sha256_file", fail_read)
    with pytest.raises(AmbiguousExportError, match="multiple ghosts exports"):
        run_report(
            config_path="nonexistent.toml",
            input_dir=tmp_path,
            no_wishlists=True,
        )


def test_report_uses_one_numbered_candidate_and_warns_for_missing_kinds(tmp_path):
    weapon = tmp_path / "destiny-weapon(7).csv"
    copyfile(SOURCE_EXPORTS["weapons"], weapon)

    result = run_report(
        config_path="nonexistent.toml",
        input_dir=tmp_path,
        no_wishlists=True,
    )

    assert [section.kind for section in result.sections] == ["weapons"]
    assert result.sections[0].source.path == str(weapon)
    assert [warning.kind for warning in result.warnings] == ["armor", "ghosts"]
    assert "destiny-armor.csv" in result.warnings[0].reason
    assert "browser-numbered copy" in result.warnings[0].reason
    assert "destiny-armor (1).csv" in result.warnings[0].reason
    assert EXPORT_PATTERNS["armor"].pattern not in result.warnings[0].reason
    snapshot = snapshot_json(result)
    assert str(tmp_path) not in snapshot
    assert EXPORT_PATTERNS["armor"].pattern not in snapshot


def test_report_with_no_candidates_reports_every_expected_browser_name(tmp_path):
    with pytest.raises(NoExportsError) as raised:
        run_report(
            config_path="nonexistent.toml",
            input_dir=tmp_path,
            no_wishlists=True,
        )

    message = str(raised.value)
    for kind, filename in EXPORT_FILENAMES.items():
        assert kind in message
        assert filename in message
        numbered_name = f"{Path(filename).stem} (1).csv"
        assert numbered_name in message
        assert "browser-numbered copy" in message
        assert EXPORT_PATTERNS[kind].pattern not in message
