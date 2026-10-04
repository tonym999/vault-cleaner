"""Runs inside the fresh environment that ``proof_e7_wheel.py`` builds.

Usage: python wheel_probe.py SPIKE_DIR FIXTURE REPO_ROOT ENVIRONMENT MARKER

Only the spike's own modules are imported from ``SPIKE_DIR``; they are not
part of the wheel.  ``vault_cleaner`` and every template must come from the
installed package.
"""

from __future__ import annotations

import http.cookiejar
import json
import sys
import tempfile
import threading
import urllib.request
from importlib.resources import files
from pathlib import Path


def main() -> int:
    spike_dir, fixture, repo, environment, marker = sys.argv[1:6]
    sys.path.insert(0, spike_dir)
    from render_env import TEMPLATE_NAMES, package_source
    from spike_app import FRAGMENT_PATH, SHELL_PATH, build_spike_server

    import vault_cleaner
    from vault_cleaner.server.session import Session

    origin = str(Path(vault_cleaner.__file__).resolve())
    print(f"vault_cleaner imported from the fresh environment: {environment in origin}; "
          f"from the repository: {repo in origin}")
    if repo in origin or environment not in origin:
        print("FAIL: the probe did not import the installed package")
        return 1

    templates = files("vault_cleaner.ui").joinpath("templates")
    present = {name: templates.joinpath(name).is_file() for name in TEMPLATE_NAMES}
    print(f"allow-listed templates present as package resources: {sum(present.values())} of {len(present)}")
    if not all(present.values()):
        print(f"FAIL: missing package resources: {[n for n, ok in present.items() if not ok]}")
        return 1

    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-137-probe-") as raw:
        root = Path(raw)
        config = root / "config.toml"
        config.write_text("", encoding="utf-8")
        session = Session(
            overrides_path=str(root / "overrides.json"),
            config_path=str(config),
            no_wishlists=True,
        )
        server = build_spike_server(
            session, 0, template_source=package_source("vault_cleaner.ui", "templates")
        )
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            base = session.expected_origin
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            opener.open(f"{base}/bootstrap?token={session.bootstrap_token}", timeout=10).read()
            upload = urllib.request.Request(
                f"{base}/api/exports/armor",
                data=Path(fixture).read_bytes(),
                headers={"Origin": base, "Content-Type": "text/csv"},
            )
            envelope = json.load(opener.open(upload, timeout=30))
            shell = opener.open(base + SHELL_PATH, timeout=10)
            shell_body = shell.read().decode("utf-8")
            fragment = opener.open(base + FRAGMENT_PATH, timeout=10)
            body = fragment.read().decode("utf-8")
            checks = {
                "shell served (HTTP 200, text/html)": shell.status == 200
                and shell.headers["Content-Type"] == "text/html; charset=utf-8"
                and "issue 137 spike" in shell_body,
                "fragment served (HTTP 200, text/html)": fragment.status == 200
                and fragment.headers["Content-Type"] == "text/html; charset=utf-8",
                "fragment carries the wheel-only marker": marker in body,
                "fragment renders the uploaded report": 'data-group-id="exact_duplicate:6031"' in body,
                "fragment revision header equals the envelope": fragment.headers[
                    "Vault-Cleaner-Report-Revision"
                ]
                == str(envelope["report_revision"]),
                "fragment keeps the production CSP": "form-action 'none'"
                in fragment.headers["Content-Security-Policy"],
            }
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            session.close()
    for label, passed in checks.items():
        print(f"{label}: {passed}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
