"""Regenerate the fake-data report golden, byte-stably, on any platform.

Run it as `python scripts/regenerate_report_snapshot.py` from the repo root
(any interpreter with the project installed). It exists because the previous
documented one-liner was POSIX-only twice over: `.venv/bin/python` does not
exist on Windows, and PowerShell re-encodes and re-terminates redirected
output, which would have corrupted the golden's bytes (#45, #53).

Deliberately independent of `tests/` — a maintenance command should not
import a test module to do its job. The build recipe is duplicated from
`tests.test_report_run.build_report` on purpose, and
`test_regeneration_script_reproduces_the_committed_golden` pins the two
against each other: if either side drifts, the byte comparison fails.
"""

from __future__ import annotations

import json
from pathlib import Path

from vault_cleaner.report_run import run_report, snapshot_dict

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
GOLDEN = FIXTURES / "report_snapshot_v1.json"


def write_golden(path: Path = GOLDEN) -> Path:
    """Write the snapshot as sorted, indented JSON: UTF-8, LF, one trailing \\n.

    `write_bytes` rather than text mode, so no platform can translate the
    line endings between here and the disk.
    """
    run = run_report(
        config_path=REPO / "nonexistent.toml",
        weapons_path=FIXTURES / "weapons_dupes.csv",
        armor_path=FIXTURES / "armor.csv",
        ghosts_path=FIXTURES / "ghosts_cleanup.csv",
        no_wishlists=True,
    )
    document = json.dumps(snapshot_dict(run), indent=2, sort_keys=True) + "\n"
    path.write_bytes(document.encode("utf-8"))
    return path


if __name__ == "__main__":
    print(f"wrote {write_golden()}")
