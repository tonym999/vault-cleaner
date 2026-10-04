"""The development loop: edit a component, see it against the real server.

    .venv/bin/python spikes/issue-206/dev.py [--fixture NAME.csv] [--port 5173]

One command starts two processes and prints one link to open:

* the unmodified Flask review server (the spike app), on a free loopback
  port, with a fake fixture already uploaded so there is data to look at;
* Vite's development server on ``127.0.0.1:5173``, which serves the Svelte
  source with hot module replacement and proxies ``/api`` and ``/bootstrap``
  to the Flask server.

How the proxy satisfies the server's checks, exactly (``vite.config.ts``,
``server.proxy``): the Flask server only accepts a request whose ``Host`` is
its own and, for a ``POST``, whose ``Origin`` is its own.  The proxy sends
the Flask server's ``Host``, and rewrites ``Origin`` **only when it equals
the dev server's own origin**; any other ``Origin`` is forwarded unchanged
and Flask refuses it.  The session cookie works on both ports because
cookies are not scoped by port.

The ``Host`` check is the one thing the loop does weaken, in development
only.  Because the proxy always presents the Flask server's ``Host``, Flask's
exact-``Host`` check no longer sees what the browser sent.  Its stand-in is
Vite's own allow-list (``server.allowedHosts``, left at its default), which
refuses a foreign name but accepts ``localhost`` and any ``*.localhost``
name; Flask itself refuses those (experiment S10 measures both).

Nothing on the Flask side is relaxed: it is the same app the proofs run.
The relaxation is the proxy, it exists only in Vite's ``server`` options,
and ``vite build`` puts none of it in the output (experiment S10 checks).
In development the page is served by Vite, so the Flask CSP does not apply
to it; the CSP is proved on the built page (S7, S8).

Fake fixtures only.  Stop with Ctrl-C.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import harness

DEV_HOST = "127.0.0.1"


def preload(live: harness.LiveSpike, fixture: str) -> None:
    """Upload a fake fixture with the session's own cookie, as the page would."""
    request = urllib.request.Request(
        f"{live.origin}/api/exports/armor",
        data=(harness.FIXTURES / fixture).read_bytes(),
        headers={
            "Origin": live.origin,
            "Content-Type": "text/csv",
            "Cookie": f"vault_cleaner_session={live.session.session_token}",
        },
    )
    urllib.request.urlopen(request, timeout=30).read()


@contextmanager
def vite_dev(frontend: Path, backend: str, port: int) -> Iterator[subprocess.Popen]:
    """Run ``vite`` in ``frontend`` with the proxy pointed at ``backend``."""
    environment = dict(os.environ, VC_SPIKE_BACKEND=backend, VC_SPIKE_DEV_PORT=str(port))
    process = subprocess.Popen(
        ["npx", "vite", "--clearScreen", "false"], cwd=frontend, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        for line in process.stdout:
            if "ready in" in line or "Local:" in line:
                break
        yield process
    finally:
        process.terminate()
        process.wait(timeout=10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--fixture", default="armor_close.csv", choices=harness.SLICE_FIXTURES)
    parser.add_argument("--port", type=int, default=5173)
    arguments = parser.parse_args()
    if not (harness.FRONTEND / "node_modules").is_dir():
        subprocess.run(["npm", "ci"], cwd=harness.FRONTEND, check=True)
    harness.FRONTEND.joinpath("dist", "assets").mkdir(parents=True, exist_ok=True)
    if not (harness.FRONTEND / "dist" / "index.html").is_file():
        subprocess.run(["npm", "run", "build"], cwd=harness.FRONTEND, check=True)
    with harness.live_spike() as live:
        preload(live, arguments.fixture)
        with vite_dev(harness.FRONTEND, live.origin, arguments.port):
            dev = f"http://{DEV_HOST}:{arguments.port}"
            print(f"Flask review server: {live.origin} (fixture {arguments.fixture} uploaded)", flush=True)
            print(f"Vite dev server:     {dev}", flush=True)
            print(f"Open this link:      {dev}/bootstrap?token={live.session.bootstrap_token}", flush=True)
            print("Edit a file under spikes/issue-206/frontend/src/ and the page updates. Ctrl-C stops.", flush=True)
            try:
                live.server_thread_join()
            except KeyboardInterrupt:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
