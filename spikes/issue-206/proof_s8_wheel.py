"""S8: the built frontend from an installed, non-editable wheel, in a browser
(gate H6).

Modelled on ``scripts/check_wheel_install.py`` and reusing its helpers.  The
proof copies the tracked source to a temporary tree, puts the three built
files beside the existing resources in ``src/vault_cleaner/ui/``, builds a
wheel and installs it into a fresh environment.  Nothing in the repository
is changed, and ``pyproject.toml`` is not edited even in the copy: today's
``package-data`` globs (``*.css``, ``*.html``, ``*.js``) already match three
flat files.

The server is then started from that environment with a ``PATH`` that holds
only the environment's own ``bin`` directory, so Node is not on it, and
Chromium drives it: bootstrap, upload a fake fixture, wait for a group to
render, complete one acknowledged verdict.

Playwright's own driver is a Node program bundled inside the Playwright
Python package in the *repository's* environment.  It is test tooling that
drives the browser; it is not on the server's ``PATH`` and the product never
runs it.

    .venv/bin/python spikes/issue-206/proof_s8_wheel.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

from harness import (
    FIXTURES,
    REPO,
    SPIKE_DIR,
    chromium,
    finish,
    main_guard,
    require_build,
)
from spike_app import FRONTEND_DIST, PACKAGED_NAMES

PACKAGE_DATA = '"vault_cleaner.ui" = ["*.css", "*.html", "*.js"]'
EDITABLE_CHECK = (
    "import importlib.metadata as m; d = m.distribution('vault-cleaner');"
    "print('editable' in (d.read_text('direct_url.json') or ''))"
)


def load_wheel_script():
    spec = importlib.util.spec_from_file_location(
        "check_wheel_install", REPO / "scripts" / "check_wheel_install.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []
    require_build()
    script = load_wheel_script()
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-206-wheel-") as raw:
        temp = Path(raw)
        source = temp / "source"
        wheelhouse = temp / "wheelhouse"
        source.mkdir()
        wheelhouse.mkdir()
        script.copy_tracked_source(source)
        pyproject = (source / "pyproject.toml").read_text(encoding="utf-8")
        print(f"package-data in the copy is today's, unedited: {pyproject.count(PACKAGE_DATA) == 1}")
        ui = source / "src" / "vault_cleaner" / "ui"
        for built, packaged in PACKAGED_NAMES.items():
            shutil.copyfile(FRONTEND_DIST / built, ui / packaged)
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps", "--wheel-dir",
             str(wheelhouse), str(source)],
            cwd=source, env=script.clean_environment(), check=True, capture_output=True,
        )
        (wheel,) = wheelhouse.glob("vault_cleaner-*.whl")
        with zipfile.ZipFile(wheel) as archive:
            names = sorted(n for n in archive.namelist() if n.startswith("vault_cleaner/ui/"))
            same_bytes = all(
                archive.read(f"vault_cleaner/ui/{packaged}") == (FRONTEND_DIST / built).read_bytes()
                for built, packaged in PACKAGED_NAMES.items()
            )
            node_files = [n for n in archive.namelist() if "node_modules" in n or n.endswith(".svelte")]
        print(f"wheel files under vault_cleaner/ui/: {names}")
        print(f"the three frontend files in the wheel are byte-identical to the build: {same_bytes}; "
              f"node_modules or .svelte files in the wheel: {len(node_files)}")
        if not same_bytes or node_files:
            failures.append("the wheel does not hold exactly the built frontend")

        environment = temp / "environment"
        run_dir = temp / "run"
        run_dir.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)
        python = script.environment_python(environment)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", str(wheel)],
            cwd=run_dir, env=script.clean_environment(), check=True, capture_output=True,
        )
        child_env = script.clean_environment()
        child_env["PATH"] = str(python.parent)
        editable = subprocess.run(
            [str(python), "-c", EDITABLE_CHECK], cwd=run_dir, env=child_env,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        print(f"installed into a fresh environment; editable install: {editable}")

        server = subprocess.Popen(
            [str(python), str(SPIKE_DIR / "wheel_server.py"), str(SPIKE_DIR), str(REPO.resolve()),
             str(environment.resolve())],
            cwd=run_dir, env=child_env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True,
        )
        try:
            facts = json.loads(server.stdout.readline())
            print(f"server process: vault_cleaner imported from the fresh environment="
                  f"{facts['package_from_environment']}, from the repository="
                  f"{facts['package_from_repository']}; node on its PATH={facts['node_on_path']}; "
                  f"npm on its PATH={facts['npm_on_path']}; frontend files found as package "
                  f"resources={facts['packaged_files']}")
            print(f"node on the proof's own PATH (so the absence above is real): "
                  f"{shutil.which('node') is not None}; PATH given to the server has "
                  f"{len(child_env['PATH'].split(os.pathsep))} entry")
            if (
                not facts["package_from_environment"] or facts["package_from_repository"]
                or facts["node_on_path"] is not None or editable != "False"
                or len(facts["packaged_files"]) != 3
            ):
                failures.append("the server did not run from the installed wheel without Node")

            origin = facts["origin"]
            with chromium() as browser:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                context.add_init_script(
                    "window.__csp = []; document.addEventListener('securitypolicyviolation',"
                    " (event) => window.__csp.push(event.effectiveDirective));"
                )
                page = context.new_page()
                console: list[str] = []
                responses: list[str] = []
                page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda error: console.append(str(error)))
                page.on("response", lambda r: responses.append(
                    f"{r.url.replace(origin, '').split('?')[0]} {r.status} {r.headers.get('content-type', '')}"))
                page.goto(facts["bootstrap"], wait_until="domcontentloaded")
                uploaded = context.request.post(
                    f"{origin}/api/exports/armor",
                    headers={"Origin": origin, "Content-Type": "text/csv"},
                    data=(FIXTURES / "armor_close.csv").read_bytes(),
                )
                print(f"bootstrap exchanged in the browser; fake fixture uploaded: HTTP {uploaded.status}")
                responses.clear()
                page.goto(f"{origin}/spike/", wait_until="domcontentloaded")
                page.wait_for_selector("article[data-group]")
                groups = page.locator("article[data-group]").evaluate_all(
                    "nodes => nodes.map((node) => node.getAttribute('data-group'))")
                print(f"groups rendered by the installed JavaScript and CSS: {groups}")
                for line in responses:
                    print(f"  response: {line}")
                before = context.request.get(f"{origin}/api/report").json()["verdict_revision"]
                page.get_by_role("button", name="Veto item 6032", exact=True).click()
                page.wait_for_function(
                    "() => document.getElementById('vc-status').textContent.includes('recorded your veto')")
                after = context.request.get(f"{origin}/api/report").json()
                pressed = page.get_by_role("button", name="Veto item 6032", exact=True).get_attribute("aria-pressed")
                styled = page.evaluate("() => getComputedStyle(document.querySelector('.btn')).borderRadius !== '0px'")
                print(f"verdict acknowledged: status={page.locator('#vc-status').text_content().strip()!r}; "
                      f"Veto pressed={pressed}; server verdict_revision {before} -> {after['verdict_revision']}; "
                      f"server verdicts={after['verdicts']}")
                violations = page.evaluate("() => window.__csp.slice()")
                print(f"stylesheet applied: {styled}; console errors: {console}; CSP violations: {violations}")
                assets = [line for line in responses if line.startswith("/spike/")]
                if (
                    groups != ["exact:6031", "same_stat:6081"]
                    or after["verdict_revision"] != before + 1
                    or after["verdicts"] != [{"id": "6032", "verdict": "vetoed"}]
                    or pressed != "true" or not styled or console or violations
                    or sorted(assets) != [
                        "/spike/ 200 text/html; charset=utf-8",
                        "/spike/assets/app.css 200 text/css; charset=utf-8",
                        "/spike/assets/app.js 200 text/javascript; charset=utf-8",
                    ]
                ):
                    failures.append("the browser run against the installed wheel did not complete cleanly")
                context.close()
        finally:
            server.stdin.close()
            server.wait(timeout=15)
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
