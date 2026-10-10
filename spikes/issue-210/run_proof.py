"""Run a fixed #206 proof, unedited, against the #210 source and build.

    .venv/bin/python spikes/issue-210/run_proof.py S1

The proofs and their oracle live in ``spikes/issue-206/`` and are not edited.
This runner points the harness's call-time build globals at the #210
frontend, then imports the proof. It accepts one fixed proof name and
forwards nothing else, so no proof can be handed a path or ``--screenshots``.

One oracle adaptation is made here, and only this one (plan, *The one proof
adaptation*): direction D prints a single "Tuned stat" value per piece.
``merge_tuned_stat`` is the whole of it.
"""

from __future__ import annotations

import importlib
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRONTEND = HERE / "frontend"
PROOFS = {
    "S1": "proof_s1_parity",
    "S2": "proof_s2_hostile",
    "S3": "proof_s3_acknowledged",
    "S4": "proof_s4_lifecycle",
    "S5": "proof_s5_focus",
    "S6": "proof_s6_layout",
    "S7": "proof_s7_csp",
    "S13": "proof_s13_axe",
    "S15": "proof_s15_scale",
    "source": "check_source",
}
S15_SECONDS = 900


def tuning_agrees(members: list[dict]) -> bool:
    """Every piece's Tuning Stat is its Tuning Mod Slot, ignoring case."""
    return all(
        member["tuning_stat"].casefold() == member["tuning_mod_slot"].casefold()
        for member in members
    )


def merge_tuned_stat(original):
    """Wrap the oracle's ``_group`` for the merged tuned-stat cell.

    When every piece of a same-stat group agrees, the page carries one value
    (``data-field="tuning_mod_slot"`` with ``data-merged="tuning_stat"``) and
    the separate ``tuning_stat`` requirement is dropped for that group. When
    any piece differs, the oracle's result is returned untouched, so both
    values are required as before.
    """

    def group(kind, raw, proposals, verdicts, persisted):
        wanted = original(kind, raw, proposals, verdicts, persisted)
        if kind != "same_stat" or not tuning_agrees(raw["members"]):
            return wanted
        wanted["shared"].pop("tuning_stat", None)
        wanted["differing"] = [name for name in wanted["differing"] if name != "tuning_stat"]
        for member in wanted["members"]:
            member["differing"].pop("tuning_stat", None)
        return wanted

    return group


def configure(frontend: Path = FRONTEND) -> None:
    """Set call-time build globals before importing any unchanged proof."""
    sys.path.insert(0, str(HERE.parent / "issue-206"))
    import expected
    import harness
    import spike_app

    harness.FRONTEND = frontend
    harness.FRONTEND_DIST = frontend / "dist"
    spike_app.FRONTEND_DIST = frontend / "dist"
    expected._group = merge_tuned_stat(expected._group)


def bounded_s15() -> int:
    """S15 in its own process group, so a hang cannot outlive this runner."""
    code = (
        "import sys\n"
        "from run_proof import configure\n"
        "configure()\n"
        "import proof_s15_scale as proof\n"
        "sys.argv = [proof.__file__]\n"
        "sys.exit(proof.main())\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-u", "-c", code], cwd=HERE, start_new_session=True
    )
    try:
        return process.wait(timeout=S15_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        print(f"RESULT: FAIL (S15 did not finish within {S15_SECONDS}s)", flush=True)
        return 1


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in PROOFS:
        print("usage: run_proof.py {" + ",".join(PROOFS) + "}")
        print("RESULT: FAIL")
        return 1
    if sys.argv[1] == "S15":
        return bounded_s15()
    configure()
    proof = importlib.import_module(PROOFS[sys.argv[1]])
    if sys.argv[1] == "source":
        proof.SOURCE = FRONTEND / "src"
        proof.DIST = FRONTEND / "dist"
    sys.argv = [proof.__file__]
    return proof.main()


if __name__ == "__main__":
    sys.exit(main())
