"""Run a fixed #206 proof unchanged against the #209 source and build."""

from __future__ import annotations

import importlib
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
    configure()
    proof = importlib.import_module(PROOFS[sys.argv[1]])
    if sys.argv[1] == "source":
        proof.SOURCE = FRONTEND / "src"
        proof.DIST = FRONTEND / "dist"
    # In particular do not pass --screenshots to a #206 proof.
    sys.argv = [proof.__file__]
    return proof.main()


if __name__ == "__main__":
    sys.exit(main())
