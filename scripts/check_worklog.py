"""Worklog layout and pull-request check (#193).

The worklog is one Markdown file per entry under ``worklog/``, named
``YYYY-MM-DD-issue-N-<slug>.md`` (or ``YYYY-MM-DD-<slug>.md`` when the work
has no issue). ``WORKLOG.md`` at the repository root is a frozen archive of
every earlier entry; its content is pinned by SHA-256 so it cannot be edited.

Tree rules always run:

* T1  ``WORKLOG.md`` is present and matches the pinned hash.
* T2  ``worklog/`` is a directory that holds at least one entry file.
* T3  Everything in ``worklog/`` is a regular file with a valid entry name.
* T4  Each entry is UTF-8 and starts with ``# YYYY-MM-DD — <title>``, the
      date matching the file name.

Pull-request rules run only with ``--base REV``, over the diff of ``worklog/``
between ``REV...HEAD``:

* P1  The pull request adds at least one valid entry file.
* P2  No entry is deleted or renamed.
* P3  No entry already on the base is edited (a correction is a new entry).

There is no way to relax a rule from outside this script. Every error is
reported, not just the first, as ``error: <message>`` on stderr; the exit
status is 0 with no errors and 1 otherwise, including when ``git`` fails.

Stdlib-only: no import of ``vault_cleaner`` or any third-party package, so CI
can run it with a bare ``python3``.

    python3 scripts/check_worklog.py [--base REV] [--root PATH]
                                     [--archive-sha256 HEX]

``--root`` and ``--archive-sha256`` exist for tests; CI passes neither.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ARCHIVE_NAME = "WORKLOG.md"
ENTRY_DIR = "worklog"

# SHA-256 of WORKLOG.md with every CRLF replaced by LF. A deliberate later
# change to the archive must change this constant in the same pull request.
ARCHIVE_SHA256 = "e4965ab13f3625c471b72228880c49ea1ec21f830688f54f53c803db30b13d0b"

# The "issue-" prefix is reserved: after the date a name has either a valid
# "issue-N-" part followed by a slug, or a slug that does not begin "issue-".
NAME_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})-(?:issue-[1-9]\d*-|(?!issue-))[a-z0-9]+(?:-[a-z0-9]+)*\.md$",
    re.ASCII,
)
HEADING_RE = re.compile(r"^# (\d{4}-\d{2}-\d{2}) — \S.*$", re.ASCII)

POINTER = "see AGENTS.md, *Worklog*"


class GitError(RuntimeError):
    """``git`` could not be run or reported a failure."""


def _name_date(name: str) -> tuple[str | None, str | None]:
    """Return (date text, error) for an entry file name."""
    match = NAME_RE.fullmatch(name)
    if match is None:
        return None, (
            f"{ENTRY_DIR}/{name}: name does not match "
            "YYYY-MM-DD-issue-N-<slug>.md or YYYY-MM-DD-<slug>.md"
        )
    text = match.group(1)
    try:
        date.fromisoformat(text)
    except ValueError:
        return None, f"{ENTRY_DIR}/{name}: {text} is not a real calendar date"
    return text, None


def check_entry(path: Path) -> list[str]:
    """Apply T3 (regular file, valid name and date) and T4 to one entry."""
    name = path.name
    label = f"{ENTRY_DIR}/{name}"
    if path.is_symlink() or not path.is_file():
        return [f"{label}: must be a regular file (no subdirectories or symlinks)"]
    name_date, error = _name_date(name)
    if error is not None:
        return [error]
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"{label}: cannot be read: {exc}"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [f"{label}: is not valid UTF-8"]
    # Split on LF only: str.splitlines() also splits on U+2028 and friends.
    first_line = text.split("\n", 1)[0]
    first_line = first_line.removesuffix("\r")
    heading = HEADING_RE.fullmatch(first_line)
    if heading is None:
        return [f"{label}: first line must be '# YYYY-MM-DD — <title>' (em dash)"]
    if heading.group(1) != name_date:
        return [
            (
                f"{label}: heading date {heading.group(1)} differs from the "
                f"file name date {name_date}"
            )
        ]
    return []


def check_archive(root: Path, expected_sha256: str) -> list[str]:
    """T1: the archive exists and its normalised bytes match the pinned hash."""
    archive = root / ARCHIVE_NAME
    frozen = (
        f"{ARCHIVE_NAME} is a frozen archive: new entries go in files under "
        f"{ENTRY_DIR}/ ({POINTER})"
    )
    try:
        raw = archive.read_bytes()
    except OSError:
        return [f"{ARCHIVE_NAME} is missing; {frozen}"]
    digest = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if digest != expected_sha256.lower():
        return [f"{ARCHIVE_NAME} has changed (sha256 {digest}); {frozen}"]
    return []


def check_tree(root: Path, expected_sha256: str = ARCHIVE_SHA256) -> list[str]:
    """Rules T1-T4 over a checked-out tree."""
    errors = check_archive(root, expected_sha256)
    directory = root / ENTRY_DIR
    if not directory.is_dir():
        errors.append(f"{ENTRY_DIR}/ is missing or is not a directory")
        return errors
    members = sorted(directory.iterdir(), key=lambda p: p.name)
    for member in members:
        errors.extend(check_entry(member))
    if not any(
        member.is_file() and not member.is_symlink() and NAME_RE.fullmatch(member.name)
        for member in members
    ):
        errors.append(f"{ENTRY_DIR}/ holds no entry file")
    return errors


def parse_name_status(output: str) -> list[tuple[str, str]]:
    """Parse ``git diff --name-status -z`` output into (status, path) pairs."""
    fields = output.split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    if len(fields) % 2 != 0:
        raise GitError("unexpected git diff output: odd number of fields")
    return [(fields[i], fields[i + 1]) for i in range(0, len(fields), 2)]


def git_changes(root: Path, base: str) -> list[tuple[str, str]]:
    """Return (status, path) for ``worklog/`` between ``base...HEAD``.

    ``--no-renames`` makes a rename appear as a delete plus an add, so P2
    catches it. Paths use ``/`` on every platform.
    """
    if base.startswith("-"):
        raise GitError(f"invalid base revision {base!r}")
    try:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-status",
                "--no-renames",
                "-z",
                f"{base}...HEAD",
                "--",
                ENTRY_DIR,
            ],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise GitError(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git diff against {base!r} failed: {detail}")
    return parse_name_status(result.stdout.decode("utf-8"))


def check_changes(root: Path, changes: list[tuple[str, str]]) -> list[str]:
    """Rules P1-P3 over a list of (status, path) changes."""
    prefix = f"{ENTRY_DIR}/"
    scoped = [(status, path) for status, path in changes if path.startswith(prefix)]
    errors: list[str] = []
    for status, path in scoped:
        if status == "D":
            errors.append(
                f"{path}: entries on the base branch must not be deleted or renamed"
            )
        elif status != "A":
            errors.append(
                f"{path}: an entry already on the base branch must not be edited "
                "(status "
                f"{status}); put the correction in a new entry file"
            )
    added_ok = False
    for status, path in scoped:
        if status != "A":
            continue
        name = path[len(prefix) :]
        if "/" not in name and not check_entry(root / ENTRY_DIR / name):
            added_ok = True
            break
    if not added_ok:
        errors.append(
            "pull request must add a valid worklog entry file under "
            f"{ENTRY_DIR}/; {ARCHIVE_NAME} is a frozen archive ({POINTER})"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--base", help="base revision; enables the pull-request rules P1-P3"
    )
    parser.add_argument("--root", type=Path, default=REPO, help="repository root")
    parser.add_argument(
        "--archive-sha256",
        default=ARCHIVE_SHA256,
        help="expected WORKLOG.md hash (for tests)",
    )
    args = parser.parse_args(argv)

    errors = check_tree(args.root, args.archive_sha256)
    if args.base is not None:
        try:
            changes = git_changes(args.root, args.base)
        except GitError as exc:
            errors.append(str(exc))
        else:
            errors.extend(check_changes(args.root, changes))

    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    if errors:
        return 1
    print("worklog: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
