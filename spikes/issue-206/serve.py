"""Try it: build the frontend and serve the proof.

    .venv/bin/python spikes/issue-206/serve.py [--fixture NAME.csv]

It runs ``npm ci`` (first time only) and ``npm run build`` in ``frontend/``,
starts the unmodified review server with the built frontend added at
``/spike/``, uploads a fake fixture, and prints two links: the one-time
sign-in link, which lands on the current production page, and the spike page
in the same session.  Fake fixtures only.  Stop with Ctrl-C.
"""

from __future__ import annotations

import argparse
import subprocess

import harness
from dev import preload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fixture", default="armor_close.csv", choices=harness.SLICE_FIXTURES)
    arguments = parser.parse_args()
    if not (harness.FRONTEND / "node_modules").is_dir():
        subprocess.run(["npm", "ci"], cwd=harness.FRONTEND, check=True)
    subprocess.run(["npm", "run", "build"], cwd=harness.FRONTEND, check=True)
    with harness.live_spike() as live:
        preload(live, arguments.fixture)
        print(f"\nFixture {arguments.fixture} is uploaded.", flush=True)
        print(f"1. Sign in (one use; shows the current page): {live.bootstrap_url}", flush=True)
        print(f"2. Then open the Svelte slice:                {live.origin}/spike/", flush=True)
        print("Ctrl-C stops the server.", flush=True)
        try:
            live.server_thread_join()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
