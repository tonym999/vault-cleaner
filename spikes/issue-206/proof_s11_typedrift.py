"""S11: how a Python-side rename reaches the browser code (gate H9).

The proof renames one envelope field on the Python side, in memory only:
an exact-group member's ``disposition`` becomes ``member_disposition`` in
what ``snapshot_dict`` returns.  ``src/`` is not edited.  It then walks the
steps a contributor would take and records where the mismatch shows:

1. ``contract.py --check`` (Python, no Node): are the committed samples
   still what the server returns?
2. after regenerating the samples into a throwaway copy of the frontend:
   the type check, the unit tests, and the production build.

    .venv/bin/python spikes/issue-206/proof_s11_typedrift.py
"""

from __future__ import annotations

import re
import subprocess

import contract
from harness import finish, frontend_copy, main_guard

from vault_cleaner import report_run

OLD, NEW = "disposition", "member_disposition"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def renamed(original):
    def snapshot(group):
        data = original(group)
        for member in data["members"]:
            member[NEW] = member.pop(OLD)
        return data

    return snapshot


def run(command: list[str], cwd) -> tuple[int, list[str]]:
    done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    lines = [ANSI.sub("", line).rstrip() for line in (done.stdout + done.stderr).splitlines()]
    return done.returncode, [line.replace(str(cwd), "frontend") for line in lines if line.strip()]


def main() -> int:
    failures: list[str] = []
    print("-- before the rename --")
    stale = [name for name, envelope in contract.generate().items()
             if (contract.SAMPLES / name).read_text(encoding="utf-8") != contract.render(envelope)]
    print(f"committed samples equal what the server returns: {not stale}")
    if stale:
        failures.append("the committed contract samples are stale; run contract.py")

    original = report_run._exact_duplicate_group_snapshot
    report_run._exact_duplicate_group_snapshot = renamed(original)
    try:
        print(f"-- Python renames exact-group member `{OLD}` to `{NEW}` --")
        drifted = contract.generate()
        stale = [name for name, envelope in drifted.items()
                 if (contract.SAMPLES / name).read_text(encoding="utf-8") != contract.render(envelope)]
        print(f"1. contract.py --check, no Node needed: stale samples detected: {stale}")
        if len(stale) != 2:
            failures.append("the Python-side contract check missed the rename")

        with frontend_copy() as frontend:
            for name, envelope in drifted.items():
                (frontend / "src" / "contract" / name).write_text(contract.render(envelope), encoding="utf-8")
            code, lines = run(["npm", "run", "check"], frontend)
            errors = [line.split(" ", 1)[1] for line in lines if " ERROR " in line]
            summary = next(line.split(" ", 1)[1] for line in lines if "COMPLETED" in line)
            print(f"2. type check after regenerating the samples: exit {code}: {summary}")
            for line in errors:
                where = line.split('"')[1] + " " + line.split('"')[2].strip()
                cause = re.search(r"Property '\w+' is missing in type .{0,40}", line)
                print(f"   {where}: ... {cause.group(0) if cause else line[:200]} ...")
                required = re.search(r"but required in type '\w+'", line)
                print(f"       ... {required.group(0) if required else ''}")
            if code == 0 or not any("samples.ts" in line and OLD in line for line in errors):
                failures.append("the type check did not catch the rename")

            code, lines = run(["npm", "test"], frontend)
            counts = [line.strip() for line in lines if line.strip().startswith(("Test Files", "Tests"))]
            print(f"3. unit tests: exit {code}: {counts}")
            if code == 0:
                failures.append("the unit tests did not catch the rename")

            code, lines = run(["npm", "run", "build"], frontend)
            built = next((line.strip() for line in lines if "built in" in line), lines[-1])
            built = re.sub(r"in \d+ms", "", built).strip()
            print(f"4. production build: exit {code}: {built} "
                  "(Vite does not type-check; the build is not the gate)")
    finally:
        report_run._exact_duplicate_group_snapshot = original
    print("so the rename surfaces at step 1 without Node, and at the type check and the unit "
          "tests with it; nothing reaches the browser unless all three are skipped")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
