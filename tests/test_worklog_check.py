"""Tests for the worklog checker (scripts/check_worklog.py, #193)."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


wl = _load_module("check_worklog", SCRIPTS / "check_worklog.py")

ARCHIVE_TEXT = (
    "# Worklog\n"
    "\n"
    "Newest first.\n"
    "\n"
    "## 2026-09-01 — #1 first\n"
    "\n"
    "Body line one.\n"
    "Body line two.\n"
    "\n"
    "## 2026-08-01 — #2 second\n"
    "\n"
    "Older body.\n"
)
ENTRY_NAME = "2026-10-04-issue-193-implementation.md"
ENTRY_TEXT = "# 2026-10-04 — #193 implementation\n\nBody.\n"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


ARCHIVE_SHA = _sha(ARCHIVE_TEXT)


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    path.write_bytes(data)


def _tree(tmp_path: Path, *, archive: str | None = ARCHIVE_TEXT) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    if archive is not None:
        _write(root / "WORKLOG.md", archive)
    return root


def _entry(root: Path, name: str = ENTRY_NAME, text: str | None = None) -> Path:
    if text is None:
        text = f"# {name[:10]} — title\n\nBody.\n"
    path = root / "worklog" / name
    _write(path, text)
    return path


def _tree_errors(root: Path, sha: str = ARCHIVE_SHA) -> list[str]:
    return wl.check_tree(root, sha)


def _has(errors: list[str], fragment: str) -> bool:
    return any(fragment in e for e in errors)


# --- Tree rules ------------------------------------------------------------


def test_valid_tree_passes(tmp_path):
    root = _tree(tmp_path)
    _entry(root, "2026-10-04-issue-193-implementation.md")
    _entry(root, "2026-10-04-housekeeping.md")
    assert _tree_errors(root) == []


def test_real_repository_passes_tree_rules():
    assert wl.check_tree(REPO) == []


def test_t1_missing_archive(tmp_path):
    root = _tree(tmp_path, archive=None)
    _entry(root)
    errors = _tree_errors(root)
    assert _has(errors, "WORKLOG.md is missing")
    assert _has(errors, "frozen archive")
    assert _has(errors, "AGENTS.md")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.replace("Body line one.", "Body line 1."),
        lambda t: t.replace("Body line two.\n", ""),
        lambda t: t.replace(
            "# Worklog\n\n", "# Worklog\n\n## 2026-10-04 — #193 new\n\n"
        ),
        lambda t: t + "x",
    ],
    ids=["edited-line", "deleted-line", "inserted-entry", "appended-byte"],
)
def test_t1_changed_archive_fails(tmp_path, mutate):
    root = _tree(tmp_path, archive=mutate(ARCHIVE_TEXT))
    _entry(root)
    errors = _tree_errors(root)
    assert _has(errors, "WORKLOG.md has changed")
    assert _has(errors, "frozen archive")
    assert _has(errors, "AGENTS.md")


def test_t1_crlf_archive_passes(tmp_path):
    root = _tree(tmp_path, archive=None)
    _write(root / "WORKLOG.md", ARCHIVE_TEXT.replace("\n", "\r\n"))
    _entry(root)
    assert _tree_errors(root) == []


def test_t2_missing_worklog_directory(tmp_path):
    root = _tree(tmp_path)
    assert _has(_tree_errors(root), "worklog/ is missing")


def test_t2_empty_worklog_directory(tmp_path):
    root = _tree(tmp_path)
    (root / "worklog").mkdir()
    assert _has(_tree_errors(root), "holds no entry file")


def test_t2_worklog_is_a_file(tmp_path):
    root = _tree(tmp_path)
    _write(root / "worklog", "not a directory")
    assert _has(_tree_errors(root), "worklog/ is missing")


@pytest.mark.parametrize(
    "name",
    [
        "2026-10-04-issue-193-fix-round-2.md",
        "2026-10-04-housekeeping.md",
        "2026-10-04-issues-roundup.md",
    ],
)
def test_t3_valid_names(tmp_path, name):
    root = _tree(tmp_path)
    _entry(root, name)
    assert _tree_errors(root) == []


@pytest.mark.parametrize(
    "name",
    [
        "README.md",
        "2026-10-04-Issue-193-x.md",
        "2026-10-04-issue-0-x.md",
        "2026-10-04-issue-007-x.md",
        "2026-10-04-issue-x-foo.md",
        "2026-10-04-issue-193.md",
        "2026-10-04-issue-193-.md",
        "2026-10-04-issue-193-x.txt",
        "2026-10-04--x.md",
        "2026-02-30-x.md",
        "26-10-04-x.md",
    ],
)
def test_t3_invalid_names(tmp_path, name):
    root = _tree(tmp_path)
    _entry(root, ENTRY_NAME)
    _write(root / "worklog" / name, f"# {name[:10]} — title\n")
    errors = _tree_errors(root)
    assert _has(errors, f"worklog/{name}")


def test_t3_subdirectory(tmp_path):
    root = _tree(tmp_path)
    _entry(root)
    (root / "worklog" / "2026-10-04-sub-dir.md").mkdir()
    assert _has(_tree_errors(root), "must be a regular file")


def test_t3_symlink(tmp_path):
    root = _tree(tmp_path)
    target = _entry(root)
    link = root / "worklog" / "2026-10-05-link.md"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not available on this platform")
    assert _has(_tree_errors(root), "must be a regular file")


def test_t3_name_with_trailing_newline_is_rejected():
    errors = wl.check_entry(Path("worklog") / "2026-10-04-x.md\n")
    assert errors


@pytest.mark.parametrize(
    "content",
    [
        b"",
        "## 2026-10-04 — x\n",
        "# 2026-10-04 - x\n",
        "# 2026-10-04 —\n",
        "# 2026-10-04 —  \n",
        "# 2026-10-05 — x\n",
        b"# 2026-10-04 \xe2\x80\x94 x \xff\n",
        "﻿# 2026-10-04 — x\n",
        "\n# 2026-10-04 — x\n",
    ],
    ids=[
        "empty",
        "wrong-level",
        "hyphen",
        "no-title",
        "blank-title",
        "date-mismatch",
        "invalid-utf8",
        "bom",
        "heading-not-first",
    ],
)
def test_t4_bad_first_line(tmp_path, content):
    root = _tree(tmp_path)
    _write(root / "worklog" / "2026-10-04-x.md", content)
    errors = _tree_errors(root)
    assert _has(errors, "worklog/2026-10-04-x.md")


def test_t4_crlf_first_line_passes(tmp_path):
    root = _tree(tmp_path)
    _write(root / "worklog" / "2026-10-04-x.md", "# 2026-10-04 — x\r\n\r\nBody.\r\n")
    assert _tree_errors(root) == []


def test_t4_separator_after_heading_does_not_hide_a_bad_first_line(tmp_path):
    # U+2028 would split a splitlines()-based scan; the heading must still be
    # judged on the LF-delimited first line.
    root = _tree(tmp_path)
    _write(root / "worklog" / "2026-10-04-x.md", "# 2026-10-04 — x y\n")
    assert _tree_errors(root) == []


# --- Pull-request rules (supplied change lists) -------------------------------


def _pr_tree(tmp_path: Path) -> Path:
    root = _tree(tmp_path)
    _entry(root)
    return root


def test_p1_no_changes_fails(tmp_path):
    errors = wl.check_changes(_pr_tree(tmp_path), [])
    assert _has(errors, "must add a valid worklog entry file")
    assert _has(errors, "frozen archive")
    assert _has(errors, "AGENTS.md")


def test_p1_only_modified_entry_fails(tmp_path):
    root = _pr_tree(tmp_path)
    errors = wl.check_changes(root, [("M", f"worklog/{ENTRY_NAME}")])
    assert _has(errors, "must add a valid worklog entry file")


def test_p1_added_file_with_invalid_name_fails(tmp_path):
    root = _pr_tree(tmp_path)
    _write(root / "worklog" / "notes.md", "# 2026-10-04 — x\n")
    errors = wl.check_changes(root, [("A", "worklog/notes.md")])
    assert _has(errors, "must add a valid worklog entry file")


def test_p1_added_file_with_bad_heading_fails(tmp_path):
    root = _pr_tree(tmp_path)
    _entry(root, "2026-10-05-bad.md", "no heading\n")
    errors = wl.check_changes(root, [("A", "worklog/2026-10-05-bad.md")])
    assert _has(errors, "must add a valid worklog entry file")


def test_p1_added_file_in_subdirectory_fails(tmp_path):
    root = _pr_tree(tmp_path)
    _write(root / "worklog" / "sub" / "2026-10-05-x.md", "# 2026-10-05 — x\n")
    errors = wl.check_changes(root, [("A", "worklog/sub/2026-10-05-x.md")])
    assert _has(errors, "must add a valid worklog entry file")


def test_p1_added_valid_entry_passes(tmp_path):
    root = _pr_tree(tmp_path)
    assert wl.check_changes(root, [("A", f"worklog/{ENTRY_NAME}")]) == []


def test_p2_deleted_entry_fails_even_with_a_new_entry(tmp_path):
    root = _pr_tree(tmp_path)
    errors = wl.check_changes(
        root,
        [("D", "worklog/2026-09-01-issue-1-old.md"), ("A", f"worklog/{ENTRY_NAME}")],
    )
    assert _has(errors, "must not be deleted or renamed")
    assert not _has(errors, "must add a valid worklog entry file")


def test_p3_modified_entry_fails_even_with_a_new_entry(tmp_path):
    root = _pr_tree(tmp_path)
    errors = wl.check_changes(
        root,
        [("M", "worklog/2026-09-01-issue-1-old.md"), ("A", f"worklog/{ENTRY_NAME}")],
    )
    assert _has(errors, "must not be edited")
    assert _has(errors, "new entry")


def test_p3_type_change_fails(tmp_path):
    root = _pr_tree(tmp_path)
    errors = wl.check_changes(
        root,
        [("T", "worklog/2026-09-01-issue-1-old.md"), ("A", f"worklog/{ENTRY_NAME}")],
    )
    assert _has(errors, "must not be edited")


def test_parse_name_status_pairs():
    out = "A\0worklog/a.md\0M\0worklog/b.md\0"
    assert wl.parse_name_status(out) == [("A", "worklog/a.md"), ("M", "worklog/b.md")]
    assert wl.parse_name_status("") == []
    with pytest.raises(wl.GitError):
        wl.parse_name_status("A\0")


# --- End to end with real git --------------------------------------------------


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _commit(root: Path, message: str = "change") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-m", message)


def _run(root: Path, base: str = "main") -> int:
    return wl.main(
        [f"--base={base}", f"--root={root}", f"--archive-sha256={ARCHIVE_SHA}"]
    )


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "e2e"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _write(root / "WORKLOG.md", ARCHIVE_TEXT)
    _write(root / "README.md", "readme\n")
    _write(
        root / "worklog" / "2026-09-30-issue-1-existing.md", "# 2026-09-30 — existing\n"
    )
    _commit(root, "base")
    _git(root, "checkout", "-b", "feature")
    return root


def test_e2e_unrelated_change_fails(repo, capsys):
    _write(repo / "README.md", "changed\n")
    _commit(repo)
    assert _run(repo) == 1
    assert "must add a valid worklog entry file" in capsys.readouterr().err


def test_e2e_added_entry_passes(repo):
    _entry(repo)
    _commit(repo)
    assert _run(repo) == 0


def test_e2e_extending_own_entry_passes(repo):
    path = _entry(repo)
    _commit(repo, "add entry")
    _write(path, ENTRY_TEXT + "\nFix round.\n")
    _commit(repo, "extend entry")
    assert _run(repo) == 0


def test_e2e_base_moving_on_does_not_matter(repo):
    _entry(repo)
    _commit(repo, "add entry")
    _git(repo, "checkout", "main")
    _entry(repo, "2026-10-02-issue-5-other.md")
    _commit(repo, "main moves on")
    _git(repo, "checkout", "feature")
    assert _run(repo) == 0


def test_e2e_editing_entry_on_base_fails(repo, capsys):
    _entry(repo)
    _write(
        repo / "worklog" / "2026-09-30-issue-1-existing.md",
        "# 2026-09-30 — rewritten\n",
    )
    _commit(repo)
    assert _run(repo) == 1
    assert "must not be edited" in capsys.readouterr().err


def test_e2e_renaming_entry_on_base_fails(repo, capsys):
    old = repo / "worklog" / "2026-09-30-issue-1-existing.md"
    old.rename(repo / "worklog" / "2026-09-30-issue-1-renamed.md")
    _commit(repo)
    assert _run(repo) == 1
    assert "must not be deleted or renamed" in capsys.readouterr().err


def test_e2e_editing_archive_line_fails(repo):
    _entry(repo)
    _write(repo / "WORKLOG.md", ARCHIVE_TEXT.replace("Older body.", "Rewritten body."))
    _commit(repo)
    assert _run(repo) == 1


def test_e2e_unresolvable_base_fails(repo, capsys):
    _entry(repo)
    _commit(repo)
    assert _run(repo, base="no-such-ref") == 1
    assert "failed" in capsys.readouterr().err


def test_e2e_option_like_base_is_rejected(repo, capsys):
    _entry(repo)
    _commit(repo)
    assert _run(repo, base="--output=evil") == 1
    assert "invalid base revision" in capsys.readouterr().err


def test_main_without_base_runs_tree_rules_only(tmp_path, capsys):
    root = _tree(tmp_path)
    _entry(root)
    assert wl.main(["--root", str(root), "--archive-sha256", ARCHIVE_SHA]) == 0
    assert "worklog: ok" in capsys.readouterr().out


def test_main_reports_every_error(tmp_path, capsys):
    root = _tree(tmp_path, archive=None)
    assert wl.main(["--root", str(root), "--archive-sha256", ARCHIVE_SHA]) == 1
    err = capsys.readouterr().err
    assert "WORKLOG.md is missing" in err
    assert "worklog/ is missing" in err
