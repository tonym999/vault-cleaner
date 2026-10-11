"""Run a #206 or #210 proof, unedited, against the #213 source and build.

    .venv/bin/python spikes/issue-213/run_proof.py S1

The proofs live in ``spikes/issue-206/`` and ``spikes/issue-210/`` and are
not edited. This runner points the harness at the #213 frontend, applies the
three adaptations #210's runner makes (by calling that runner's own
functions), then imports the proof. It accepts one fixed name and forwards
nothing else, so no proof can be handed a path or ``--screenshots``.

Why this file is named ``run_proof``: #210's proofs and #209's gate proof do
``from run_proof import configure`` and call it with no argument. #210's own
``configure`` binds #210's frontend as its default when it is defined, so a
caller cannot redirect it afterwards. With this directory first on the path,
that import finds this module, whose ``configure`` always means #213.

Every signed-in browser context prints the SHA-256 of the ``app.js`` and
``app.css`` the live server sent, and the run fails if they are not the #213
build's. ``build-check`` is that check's negative control.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import signal
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRONTEND = HERE / "frontend"
ISSUE_210 = HERE.parent / "issue-210"
ISSUE_206 = HERE.parent / "issue-206"
ASSETS = ("assets/app.js", "assets/app.css")
PROOFS = {
    "S1": "proof_s1_parity",
    "S2": "proof_s2_hostile",
    "S3": "proof_s3_acknowledged",
    "S4": "proof_s4_lifecycle",
    "S5": "proof_s5_focus",
    "S6": "proof_s6_layout",
    "S15": "proof_s15_scale",
    "source": "check_source",
    "csp": "proof_csp",
    "axe": "proof_axe",
    "layout": "proof_layout",
    "no-transition": "proof_no_transition",
}
S15_SECONDS = 900

_configured = False
_runner_210 = None


def runner_210():
    """#210's runner, loaded under another name so it cannot shadow this one."""
    global _runner_210
    if _runner_210 is None:
        spec = importlib.util.spec_from_file_location("run_proof_210", ISSUE_210 / "run_proof.py")
        _runner_210 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_runner_210)
    return _runner_210


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def on_disk(frontend: Path) -> tuple[str, ...] | None:
    paths = [frontend / "dist" / name for name in ASSETS]
    if not all(path.is_file() for path in paths):
        return None
    return tuple(digest(path.read_bytes()) for path in paths)


def report_build(context, live, expected: Path) -> None:
    """Print what the live server sent; fail unless it is ``expected``'s build."""
    served = tuple(
        digest(context.request.get(f"{live.origin}/spike/{name}").body()) for name in ASSETS
    )
    mine = on_disk(expected)
    print(
        f"build served: app.js sha256={served[0]} app.css sha256={served[1]}; "
        f"is the {expected.parent.name} build={served == mine}; "
        f"same bytes as the issue-210 build={served == on_disk(ISSUE_210 / 'frontend')}",
        flush=True,
    )
    if served != mine:
        print(f"RESULT: FAIL (the server did not send the {expected.parent.name} build)", flush=True)
        raise SystemExit(1)


def watch_build(expected: Path) -> None:
    """Wrap the harness's sign-in so each live server reports its build once."""
    import harness

    original = harness.authenticated_context
    seen: set[str] = set()

    def authenticated_context(browser, live, *args, **kwargs):
        context = original(browser, live, *args, **kwargs)
        if live.origin not in seen:
            seen.add(live.origin)
            report_build(context, live, expected)
        return context

    harness.authenticated_context = authenticated_context


def configure() -> None:
    """Point the unedited proofs at the #213 frontend. Safe to call again."""
    global _configured
    if _configured:
        return
    _configured = True
    runner_210().configure(FRONTEND)
    # After this directory, so `run_proof` stays this module.
    sys.path.append(str(ISSUE_210))
    watch_build(FRONTEND)


def one_column_measure() -> None:
    runner_210().one_column_measure()


def bounded_s15() -> int:
    """S15 in its own process group, so a hang cannot outlive this runner."""
    code = (
        "import sys\n"
        "from run_proof import configure, one_column_measure\n"
        "configure()\n"
        "one_column_measure()\n"
        "import proof_axe\n"
        "import proof_s15_scale as proof\n"
        "proof.axe_check = proof_axe.run\n"
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


def build_check() -> int:
    """Negative control: serve #206's build and require the check to refuse it."""
    if not (ISSUE_206 / "frontend" / "dist" / "index.html").is_file():
        print("FAIL: not built: spikes/issue-206/frontend. Run `npm ci && npm run build` there first.")
        print("RESULT: FAIL")
        return 1
    runner_210().configure(ISSUE_206 / "frontend")
    import harness

    with harness.chromium() as browser, harness.live_spike() as live:
        context = harness.authenticated_context(browser, live)
        try:
            report_build(context, live, FRONTEND)
        except SystemExit:
            print("negative control: #206's build was served and refused")
            print("RESULT: PASS")
            return 0
        finally:
            context.close()
    print("RESULT: FAIL (a build that is not #213's was accepted)")
    return 1


def main() -> int:
    names = [*PROOFS, "build-check"]
    if len(sys.argv) != 2 or sys.argv[1] not in names:
        print("usage: run_proof.py {" + ",".join(names) + "}")
        print("RESULT: FAIL")
        return 1
    name = sys.argv[1]
    if name == "build-check":
        return build_check()
    if name == "S15":
        return bounded_s15()
    configure()
    if name == "S6":
        one_column_measure()
    proof = importlib.import_module(PROOFS[name])
    if name == "source":
        proof.SOURCE = FRONTEND / "src"
        proof.DIST = FRONTEND / "dist"
    sys.argv = [proof.__file__]
    return proof.main()


if __name__ == "__main__":
    # Run as the module the proofs import, so there is one copy of the state.
    import run_proof

    sys.exit(run_proof.main())
