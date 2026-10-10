"""Run a fixed #206 proof unchanged against the #209 source and build."""

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
    "S13": "proof_s13_axe",
    "S15": "proof_s15_scale",
    "source": "check_source",
}


def wait_bounded(process: subprocess.Popen, seconds: float = 900) -> int:
    """Bound the unchanged S15; close only descendants of our isolated child."""
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        print(f"FAIL: unchanged S15 did not finish within {seconds:g}s", flush=True)
    rows = subprocess.check_output(["ps", "-eo", "pid=,ppid=,comm="], text=True)
    parents = {int(pid): (int(parent), name) for pid, parent, name in
               (row.split(maxsplit=2) for row in rows.splitlines())}
    owned = {process.pid}
    while True:
        children = {pid for pid, (parent, _) in parents.items() if parent in owned}
        if children <= owned:
            break
        owned |= children
    # Stable Linux process handles remain valid if a descendant becomes an
    # orphan; a PID reused after cleanup cannot receive our signal.
    handles = {}
    for pid in owned:
        try:
            handles[pid] = os.pidfd_open(pid)
        except ProcessLookupError:
            pass
    try:
        # Closing our browser releases Page.evaluate so the unchanged proof's
        # context managers can retire its server and staging. Exited snapshot
        # PIDs have no handle and are skipped.
        for pid, handle in handles.items():
            parent, name = parents.get(pid, (0, ""))
            if name.startswith("chrome") and not parents.get(parent, (0, ""))[1].startswith("chrome"):
                try:
                    signal.pidfd_send_signal(handle, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
    finally:
        # Handles also retire owned orphans detached from the child's group.
        for handle in handles.values():
            try:
                signal.pidfd_send_signal(handle, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(handle)
    print("RESULT: FAIL (S15 verification timeout; owned processes closed)", flush=True)
    return 1


def bounded_s15() -> int:
    code = """import sys
from run_proof import configure
configure()
import proof_s15_scale as proof
sys.argv = [proof.__file__]
try:
    result = proof.main()
except SystemExit as error:
    if error.code not in (None, 0):
        print('RESULT: FAIL (S15 exited before completion)', flush=True)
    raise
except Exception:
    print('RESULT: FAIL (S15 raised an exception)', flush=True)
    raise
sys.exit(result)
"""
    process = subprocess.Popen([sys.executable, "-u", "-c", code], cwd=HERE, start_new_session=True)
    result = wait_bounded(process)
    if result:
        print("RESULT: FAIL (S15 child returned nonzero status)", flush=True)
    return result


def configure(frontend: Path = FRONTEND) -> None:
    """Set call-time build globals before importing any unchanged proof."""
    sys.path.insert(0, str(HERE.parent / "issue-206"))
    import harness
    import spike_app

    harness.FRONTEND = frontend
    harness.FRONTEND_DIST = frontend / "dist"
    spike_app.FRONTEND_DIST = frontend / "dist"


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
    # In particular do not pass --screenshots to a #206 proof.
    sys.argv = [proof.__file__]
    return proof.main()


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit as error:
        if error.code not in (None, 0):
            print("RESULT: FAIL (proof exited before completion)", flush=True)
        raise
    except Exception:
        print("RESULT: FAIL (proof raised an exception)", flush=True)
        raise
    sys.exit(code)
