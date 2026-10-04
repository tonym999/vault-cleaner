"""S10: the development loop (gate H9).

Everything is measured on a throwaway copy of ``frontend/`` so the committed
slice is never edited.  Timings are wall-clock on this machine and vary from
run to run; everything else in the output is repeatable.

1. A cold production build and a rebuild after a one-line edit; output size.
2. ``svelte-check`` and the unit tests.
3. The edit-and-see loop that ``dev.py`` starts: the unmodified Flask server
   with a fake fixture, Vite's dev server proxying to it.  The proof signs
   in through the proxy, records a verdict through it, edits a component
   and times how long the open page takes to show the edit, without a
   reload and with the server's data still on screen.
4. What the proxy does to ``Origin``, and that a foreign ``Origin`` is still
   refused; and what stands in for Flask's exact-``Host`` check, which the
   proxy bypasses by always presenting the server's own ``Host``.
5. That none of the development path is in the build.

    .venv/bin/python spikes/issue-206/proof_s10_devloop.py
"""

from __future__ import annotations

import gzip
import http.client
import shutil
import subprocess
import time
from pathlib import Path

from dev import preload, vite_dev
from harness import chromium, finish, frontend_copy, live_spike, main_guard

DEV_PORT = 5199
EDIT_FILE = "src/App.svelte"
EDIT_FROM = "Duplicate groups\n"
EDIT_TO = "Duplicate groups (edited while running)\n"
DEV_ONLY = ("VC_SPIKE_BACKEND", "VC_SPIKE_DEV_PORT", "changeOrigin", "proxyReq", "@vite/client",
            "import.meta.hot", "5173", "__vite")


def timed(command: list[str], cwd: Path) -> tuple[float, subprocess.CompletedProcess]:
    start = time.perf_counter()
    done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return time.perf_counter() - start, done


def post(port: int, host: str, origin: str, cookie: str) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request("POST", "/api/reset", body=b"not json", headers={
        "Host": host, "Origin": origin, "Cookie": cookie, "Content-Type": "application/json"})
    status = connection.getresponse().status
    connection.close()
    return status


def get(port: int, host: str, cookie: str) -> int:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    connection.request("GET", "/api/report", headers={"Host": host, "Cookie": cookie})
    status = connection.getresponse().status
    connection.close()
    return status


def main() -> int:
    failures: list[str] = []
    with frontend_copy() as frontend:
        print("-- build --")
        shutil.rmtree(frontend / "node_modules" / ".vite", ignore_errors=True)
        cold, built = timed(["npm", "run", "build"], frontend)
        source = frontend / EDIT_FILE
        original = source.read_text(encoding="utf-8")
        if original.count(EDIT_FROM) != 1:
            print("FAIL: the edit anchor is not in App.svelte exactly once")
            return 1
        source.write_text(original.replace(EDIT_FROM, EDIT_TO), encoding="utf-8")
        again, rebuilt = timed(["npm", "run", "build"], frontend)
        source.write_text(original, encoding="utf-8")
        print(f"cold build: exit {built.returncode}, {cold:.1f} s; "
              f"rebuild after a one-line edit: exit {rebuilt.returncode}, {again:.1f} s")
        print("(each figure includes starting npm and Vite; Vite's own report of the build step "
              f"was: {built.stdout.strip().splitlines()[-1].strip()})")
        timed(["npm", "run", "build"], frontend)
        for name in ("index.html", "assets/app.js", "assets/app.css"):
            data = (frontend / "dist" / name).read_bytes()
            print(f"{name}: {len(data)} bytes, {len(gzip.compress(data, 9))} gzip")
        if built.returncode or rebuilt.returncode:
            failures.append("a build failed")

        print("-- type check and unit tests --")
        seconds, check = timed(["npm", "run", "check"], frontend)
        summary = check.stdout.strip().splitlines()[-1].split(" ", 1)[1]
        print(f"svelte-check: exit {check.returncode}, {seconds:.1f} s: {summary}")
        seconds, tests = timed(["npm", "test"], frontend)
        counts = [line.strip() for line in tests.stdout.splitlines() if "Tests" in line or "Test Files" in line]
        print(f"vitest: exit {tests.returncode}, {seconds:.1f} s: {counts}")
        if check.returncode or tests.returncode:
            failures.append("the type check or the unit tests failed")

        print("-- edit and see, against the real server --")
        with live_spike() as live, chromium() as browser:
            preload(live, "armor_close.csv")
            start = time.perf_counter()
            with vite_dev(frontend, live.origin, DEV_PORT):
                dev = f"http://127.0.0.1:{DEV_PORT}"
                context = browser.new_context()
                page = context.new_page()
                posts: list[str] = []
                page.on("request", lambda r: posts.append(f"{r.method} {r.url.replace(dev, '')}")
                        if r.method == "POST" else None)
                page.goto(f"{dev}/bootstrap?token={live.session.bootstrap_token}")
                page.wait_for_selector("article[data-group]")
                ready = time.perf_counter() - start
                print(f"one command to first render, through the proxy: {ready:.1f} s; "
                      f"page address is the dev server's: {page.url == dev + '/'}")
                page.get_by_role("button", name="Veto item 6032", exact=True).click()
                page.wait_for_function(
                    "() => document.getElementById('vc-status').textContent.includes('recorded your veto')")
                print(f"a verdict through the proxy: the page sent {posts} to the dev server; "
                      f"server verdicts={live.session.verdicts}")
                if live.session.verdicts != [{"id": "6032", "verdict": "vetoed"}]:
                    failures.append("a verdict did not reach the server through the proxy")

                page.evaluate("() => { window.__sameDocument = true; }")
                saved = time.perf_counter()
                source.write_text(original.replace(EDIT_FROM, EDIT_TO), encoding="utf-8")
                page.wait_for_function(
                    "() => document.getElementById('vc-list-title').textContent.includes('edited while running')")
                seen = time.perf_counter() - saved
                kept = page.evaluate("() => window.__sameDocument === true")
                still = page.get_by_role("button", name="Veto item 6032", exact=True).get_attribute("aria-pressed")
                print(f"save to visible: {seen * 1000:.0f} ms; no page reload: {kept}; "
                      f"the server's verdict is still shown: {still == 'true'}")
                source.write_text(original, encoding="utf-8")
                if not kept or still != "true" or seen > 5:
                    failures.append("the edit was not visible within a few seconds without a reload")

                print("-- what the proxy does to Origin --")
                cookie = f"vault_cleaner_session={live.session.session_token}"
                own = post(DEV_PORT, f"127.0.0.1:{DEV_PORT}", dev, cookie)
                foreign = post(DEV_PORT, f"127.0.0.1:{DEV_PORT}", "http://evil.example", cookie)
                direct = post(live.session.bound_port, live.session.expected_host, dev, cookie)
                print(f"POST through the proxy with the dev server's own Origin: HTTP {own} "
                      f"(reached the route; 400 is its answer to a malformed body)")
                print(f"POST through the proxy with a foreign Origin: HTTP {foreign} (forwarded unchanged, refused)")
                print(f"POST straight to Flask with the dev server's Origin: HTTP {direct} (Flask itself is not relaxed)")
                if (own, foreign, direct) != (400, 403, 403):
                    failures.append("the proxy's Origin handling is not as described")

                print("-- what stands in for Flask's exact-Host check --")
                print("the proxy always presents the Flask server's own Host, so in development the "
                      "only Host check is Vite's allow-list (server.allowedHosts, left at its default)")
                flask_port = live.session.bound_port
                through = {
                    name: get(DEV_PORT, f"{name}:{DEV_PORT}", cookie)
                    for name in ("127.0.0.1", "evil.example", "localhost", "foo.localhost")
                }
                straight = {
                    name: get(flask_port, f"{name}:{flask_port}", cookie)
                    for name in ("127.0.0.1", "evil.example", "localhost", "foo.localhost")
                }
                print(f"GET /api/report through the proxy, by Host name (dev port): {through}")
                print(f"GET /api/report straight to Flask, by Host name (its own port): {straight}")
                print("so Vite refuses a foreign Host, but accepts localhost and any *.localhost "
                      "name, which Flask itself refuses")
                if through != {"127.0.0.1": 200, "evil.example": 403, "localhost": 200, "foo.localhost": 200}:
                    failures.append("Vite's Host allow-list does not behave as recorded")
                if straight != {"127.0.0.1": 200, "evil.example": 400, "localhost": 400, "foo.localhost": 400}:
                    failures.append("Flask's own Host check does not behave as recorded")
                context.close()

        print("-- none of the development path is in the build --")
        for name in ("index.html", "assets/app.js", "assets/app.css"):
            text = (frontend / "dist" / name).read_text(encoding="utf-8")
            found = [token for token in DEV_ONLY if token in text]
            print(f"{name}: development-only strings found: {found}")
            if found:
                failures.append(f"{name} contains part of the development path")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
