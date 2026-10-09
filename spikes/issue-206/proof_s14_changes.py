"""S14: three change exercises (gate H8).

Each exercise is a patch file under ``exercises/`` against the committed
slice.  None is left applied.  For each, the proof:

* checks the patch applies cleanly to the committed slice;
* applies it to a throwaway copy and runs the type check, the unit tests
  and the build;
* counts the files and separate places (hunks) it touches, shipped code and
  tests apart;
* applies a deliberately incomplete version and records whether the type
  check or a test catches it;
* checks, at this head, each ``file:line`` where the same change would have
  to be made in the current page and in #137's Jinja hybrid.

    .venv/bin/python spikes/issue-206/proof_s14_changes.py
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from harness import FRONTEND, REPO, SPIKE_DIR, finish, frontend_copy, main_guard

EXERCISES = SPIKE_DIR / "exercises"
UI = "src/vault_cleaner/ui"
HYBRID = "spikes/issue-137"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

# (file, line, text that line must contain, what would change there)
CASES = (
    {
        "name": "1-member-value",
        "title": "show one more per-member comparison value (a same-stat member's selected partner)",
        "current": (
            (f"{UI}/review_ui.js", 569, "var selectedPartnerId = member.selected_partner_id", "already normalised here (3 lines), or it would be added"),
            (f"{UI}/review_ui.js", 592, "selectedPartnerId: selectedPartnerId", "already carried on the member, or it would be added"),
            (f"{UI}/review_ui.js", 1500, "specs.push({", "add one comparison spec after Holofoil"),
        ),
        "hybrid": (
            (f"{HYBRID}/context.py", 172, "{", "add one axis spec after Holofoil in _axes"),
        ),
    },
    {
        "name": "2-filter-facet",
        "title": "add one more filter facet (Slot / type)",
        "current": (
            (f"{UI}/review_server.js", 106, 'type: ""', "initial filter state"),
            (f"{UI}/review_server.js", 264, '"type"', "fields reconciled when a report or kind changes"),
            (f"{UI}/review_server.js", 295, "query.type", "scope sentence"),
            (f"{UI}/review_server.js", 369, 'type: ""', "filter state restored on adoption"),
            (f"{UI}/review_server.js", 1298, "vc-dup-f-type", "the control"),
            (f"{UI}/review_ui.js", 758, "q.type", "the match"),
        ),
        "hybrid": (
            (f"{HYBRID}/context.py", 382, '"guardian_class"', "the group's facet value"),
            (f"{HYBRID}/templates/_armor_group.html", 128, "data-vc-guardian-class", "the data attribute the browser filters on"),
            (f"{HYBRID}/templates/shell.html", 37, "vc-dup-f-guardianClass", "the control"),
            (f"{HYBRID}/static/spike.js", 33, "classSelect", "the control's handle"),
            (f"{HYBRID}/static/spike.js", 44, "guardianClass", "filter state"),
            (f"{HYBRID}/static/spike.js", 388, "state.guardianClass", "scope sentence"),
            (f"{HYBRID}/static/spike.js", 408, "state.guardianClass", "recount and drop"),
            (f"{HYBRID}/static/spike.js", 431, "state.guardianClass", "the match"),
            (f"{HYBRID}/static/spike.js", 465, "state.guardianClass", "the change handler"),
        ),
    },
    {
        "name": "3-verdict-wording",
        "title": "change the wording of one verdict state (Unreviewed)",
        "current": (
            (f"{UI}/review_server.js", 425, '"Unreviewed"', "the wording"),
        ),
        "hybrid": (
            (f"{HYBRID}/context.py", 101, '"Unreviewed"', "the wording"),
        ),
    },
)


def touched(patch: Path) -> tuple[dict[str, int], dict[str, int]]:
    """Hunks per file, shipped code and tests apart."""
    code: dict[str, int] = {}
    tests: dict[str, int] = {}
    current = ""
    for line in patch.read_text(encoding="utf-8").splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@"):
            bucket = tests if current.endswith(".test.ts") else code
            bucket[current] = bucket.get(current, 0) + 1
    return code, tests


def run(command: list[str], cwd: Path) -> tuple[int, list[str]]:
    done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return done.returncode, [ANSI.sub("", line) for line in (done.stdout + done.stderr).splitlines()]


def apply(patch: Path, frontend: Path, reverse: bool = False) -> int:
    command = ["patch", "-p1", "--quiet", "--input", str(patch)] + (["--reverse"] if reverse else [])
    return subprocess.run(command, cwd=frontend, capture_output=True, check=False).returncode


def anchors(label: str, places: tuple, failures: list[str]) -> None:
    files = sorted({place[0] for place in places})
    print(f"  {label}: {len(places)} places in {len(files)} files")
    for path, number, expected, what in places:
        line = (REPO / path).read_text(encoding="utf-8").splitlines()[number - 1]
        found = expected in line
        print(f"    {path}:{number} {what}: found at that line={found}")
        if not found:
            failures.append(f"{path}:{number} is not where {expected!r} is")


def source_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted((FRONTEND / "src").rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(FRONTEND).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    before = source_digest()
    with frontend_copy() as frontend:
        for case in CASES:
            patch = EXERCISES / f"{case['name']}.patch"
            incomplete = EXERCISES / f"{case['name']}.incomplete.patch"
            print(f"-- exercise {case['name'][0]}: {case['title']} --")
            clean = subprocess.run(
                ["git", "apply", "--check", "--directory=spikes/issue-206/frontend", str(patch)],
                cwd=REPO, capture_output=True, check=False,
            ).returncode == 0
            code, tests = touched(patch)
            print(f"  patch applies cleanly to the committed slice: {clean}")
            print(f"  Svelte slice: {sum(code.values())} places in {len(code)} files {code}; "
                  f"tests added or changed: {tests or 'none'}")
            if not clean or apply(patch, frontend):
                failures.append(f"{patch.name} does not apply")
                continue
            check, lines = run(["npm", "run", "check"], frontend)
            test, test_lines = run(["npm", "test"], frontend)
            build, _ = run(["npm", "run", "build"], frontend)
            counts = [line.strip() for line in test_lines if line.strip().startswith("Tests")]
            print(f"  with the patch: type check exit {check}, unit tests exit {test} {counts}, build exit {build}")
            if check or test or build:
                failures.append(f"{patch.name} breaks the slice")
            apply(patch, frontend, reverse=True)

            if apply(incomplete, frontend):
                failures.append(f"{incomplete.name} does not apply")
                continue
            check, lines = run(["npm", "run", "check"], frontend)
            test, _ = run(["npm", "test"], frontend)
            errors = [line.split(" ", 1)[1] for line in lines if " ERROR " in line]
            print(f"  deliberately incomplete version: type check exit {check}, unit tests exit {test}")
            for error in errors[:2]:
                print(f"    {error[:230]}")
            if check == 0 and test == 0:
                failures.append(f"nothing caught the incomplete version of {case['name']}")
            apply(incomplete, frontend, reverse=True)
            anchors("current page", case["current"], failures)
            anchors("Jinja hybrid (#137)", case["hybrid"], failures)
    after = source_digest()
    print(f"the committed slice is byte-identical before and after this proof: {before == after}")
    if before != after:
        failures.append("a patch was left applied to the committed slice")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
