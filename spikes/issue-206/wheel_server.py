"""Runs inside the fresh environment that ``proof_s8_wheel.py`` builds.

Usage: python wheel_server.py SPIKE_DIR REPO_ROOT ENVIRONMENT

It imports ``vault_cleaner`` from the installed wheel, serves the frontend
from the wheel's package resources, prints one line of facts and the
bootstrap URL, and serves until its standard input closes.

Only ``spike_app.py`` is imported from ``SPIKE_DIR``; it is not part of the
wheel.  The three frontend files must come from the installed package.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path


def main() -> int:
    spike_dir, repo, environment = sys.argv[1:4]
    sys.path.insert(0, spike_dir)
    from spike_app import PACKAGED_NAMES, build_spike_server, package_source

    import vault_cleaner
    from vault_cleaner.server.session import Session

    origin = str(Path(vault_cleaner.__file__).resolve())
    resources = Path(str(vault_cleaner.__file__)).resolve().parent / "ui"
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-206-wheel-run-") as raw:
        root = Path(raw)
        (root / "config.toml").write_text("", encoding="utf-8")
        session = Session(
            overrides_path=str(root / "overrides.json"),
            config_path=str(root / "config.toml"),
            no_wishlists=True,
        )
        server = build_spike_server(session, 0, read_slice=package_source())
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        print(json.dumps({
            "package_from_environment": environment in origin,
            "package_from_repository": repo in origin,
            "node_on_path": shutil.which("node"),
            "npm_on_path": shutil.which("npm"),
            "packaged_files": sorted(
                name for name in PACKAGED_NAMES.values() if (resources / name).is_file()
            ),
            "origin": session.expected_origin,
            "bootstrap": f"{session.expected_origin}/bootstrap?token={session.bootstrap_token}",
        }), flush=True)
        try:
            sys.stdin.read()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
