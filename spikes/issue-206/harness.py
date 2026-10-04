"""Shared plumbing for the #206 proof scripts.

Every proof boots the spike app (the production app plus the built frontend)
on a loopback port, with fake fixtures only.  Browser proofs use the pinned
Playwright Chromium and stop with an error when it is missing; they never
skip.  The frontend must have been built first (``npm ci && npm run build``
in ``frontend/``); a proof fails with that instruction when it has not.
"""

from __future__ import annotations

import logging
import shutil
import sys
import tempfile
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spike_app import (
    FRONTEND_DIST,
    PROBES_DIST,
    SLICE_CSP_ADDITIONS,
    build_spike_server,
)

from vault_cleaner.server import app as server_app
from vault_cleaner.server.session import Session

SPIKE_DIR = Path(__file__).resolve().parent
REPO = SPIKE_DIR.parents[1]
FRONTEND = SPIKE_DIR / "frontend"
FIXTURES = REPO / "tests" / "fixtures"
SLICE_FIXTURES = (
    "armor_close.csv",
    "armor_duplicates_ui.csv",
    "armor_same_stat_ui.csv",
    "armor_same_stat_four_ui.csv",
)
LIVE_REGIONS = ("vc-status", "vc-reconciliation", "vc-scope")

# Request logs carry the port and a timestamp; keep proof output repeatable.
logging.getLogger("werkzeug").setLevel(logging.ERROR)


@dataclass(frozen=True)
class LiveSpike:
    session: Session
    origin: str
    bootstrap_url: str
    server: Any
    root: Path
    thread: threading.Thread

    def server_thread_join(self) -> None:
        """Block until the server stops (used by the serve and dev commands)."""
        while self.thread.is_alive():
            self.thread.join(timeout=0.5)


class _StagingTempfile:
    """Keep the server's upload directories under the proof's own temp root."""

    def __init__(self, staging_root: Path) -> None:
        self._staging_root = staging_root

    def mkdtemp(self, suffix=None, prefix=None, dir=None):
        if prefix is not None and prefix.startswith("vault-cleaner-uploads-"):
            dir = self._staging_root
        return tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

    def __getattr__(self, name: str) -> object:
        return getattr(tempfile, name)


def require_build(probes: bool = False) -> None:
    missing = [
        str(path.relative_to(REPO))
        for path in ([FRONTEND_DIST / "index.html"] + ([PROBES_DIST / "plain.html"] if probes else []))
        if not path.is_file()
    ]
    if missing:
        print(f"FAIL: not built: {missing}. Run `npm ci && npm run build` in the "
              "directory first (see spikes/issue-206/README.md).")
        raise SystemExit(1)


@contextmanager
def live_spike(
    *,
    probes: bool = False,
    csp_additions: Iterable[str] = SLICE_CSP_ADDITIONS,
    port: int = 0,
    overrides: str | None = None,
) -> Iterator[LiveSpike]:
    """Serve the spike app from a thread until the block exits."""
    require_build(probes)
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-206-") as raw:
        root = Path(raw)
        staging = root / "staging"
        staging.mkdir()
        config = root / "config.toml"
        config.write_text("", encoding="utf-8")
        if overrides is not None:
            (root / "overrides.json").write_text(overrides, encoding="utf-8")
        original = server_app.tempfile
        server_app.tempfile = _StagingTempfile(staging)
        session = Session(
            overrides_path=str(root / "overrides.json"),
            config_path=str(config),
            no_wishlists=True,
            bootstrap_token="spike-bootstrap",
            session_token="spike-session",
        )
        server = build_spike_server(session, port, probes=probes, csp_additions=csp_additions)
        thread = threading.Thread(target=server.serve_forever, name="spike-206-server")
        thread.start()
        origin = session.expected_origin
        try:
            yield LiveSpike(
                session=session,
                origin=origin,
                bootstrap_url=f"{origin}/bootstrap?token={session.bootstrap_token}",
                server=server,
                root=root,
                thread=thread,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            session.close()
            server_app.tempfile = original


@contextmanager
def frontend_copy() -> Iterator[Path]:
    """A throwaway copy of ``frontend/`` for experiments that edit source.

    Source and configuration are copied; ``node_modules`` is linked.  The
    committed slice is never edited by a proof.
    """
    if not (FRONTEND / "node_modules").is_dir():
        print("FAIL: run `npm ci` in spikes/issue-206/frontend first")
        raise SystemExit(1)
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-206-frontend-") as raw:
        copy = Path(raw) / "frontend"
        shutil.copytree(FRONTEND, copy, ignore=shutil.ignore_patterns("node_modules", "dist"))
        (copy / "node_modules").symlink_to(FRONTEND / "node_modules", target_is_directory=True)
        yield copy


@contextmanager
def chromium() -> Iterator[Any]:
    """Launch the pinned Chromium, or fail.  A browser proof never skips."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except PlaywrightError as error:
            print(f"FAIL: the pinned Playwright Chromium could not be launched: {error}")
            raise SystemExit(1) from error
        try:
            yield browser
        finally:
            browser.close()


def authenticated_context(
    browser: Any, live: LiveSpike, width: int = 1440, height: int = 1000, scheme: str = "light"
):
    """A browser context that has completed the real bootstrap exchange."""
    context = browser.new_context(
        viewport={"width": width, "height": height}, color_scheme=scheme
    )
    page = context.new_page()
    page.goto(live.bootstrap_url, wait_until="domcontentloaded")
    page.close()
    return context


def upload(context: Any, live: LiveSpike, fixture: str, kind: str = "armor") -> dict:
    """Upload a fake fixture through the unmodified production route."""
    return upload_bytes(context, live, (FIXTURES / fixture).read_bytes(), kind, fixture)


def upload_bytes(
    context: Any, live: LiveSpike, body: bytes, kind: str = "armor", fixture: str = "export"
) -> dict:
    response = context.request.post(
        f"{live.origin}/api/exports/{kind}",
        headers={"Origin": live.origin, "Content-Type": "text/csv"},
        data=body,
    )
    if response.status != 200:
        raise RuntimeError(f"upload of {fixture} returned HTTP {response.status}")
    return response.json()


def api_post(context: Any, live: LiveSpike, path: str, payload: dict) -> Any:
    """A mutation made outside the page, as another tab would make it."""
    return context.request.post(
        f"{live.origin}{path}",
        headers={"Origin": live.origin, "Content-Type": "application/json"},
        data=payload,
    )


def report(context: Any, live: LiveSpike) -> dict:
    return context.request.get(f"{live.origin}/api/report").json()


def open_slice(context: Any, live: LiveSpike) -> Any:
    """The spike page, settled: its first report request has been answered."""
    page = context.new_page()
    page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
    page.wait_for_selector("#vc-status[data-connection]:not([data-connection='connecting'])")
    return page


def reload_report(page: Any) -> None:
    """Press the slice's Reload button and wait until the answer is shown."""
    with page.expect_response("**/api/report"):
        page.locator("button", has_text="Reload report").click()
    page.wait_for_selector("#vc-status[data-connection]:not([data-connection='connecting'])")
    page.wait_for_function(
        "() => document.querySelector(\"[data-busy]\").getAttribute('data-busy') === ''"
    )


def open_production_duplicates(context: Any, live: LiveSpike) -> Any:
    """The production page with its Armor duplicates surface selected."""
    page = context.new_page()
    page.goto(f"{live.origin}/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => /Connected|finalised/.test(document.getElementById('vc-status').textContent)"
    )
    page.locator("#vc-view-duplicates").click()
    return page


CSP_INIT_SCRIPT = """
window.__cspViolations = [];
document.addEventListener("securitypolicyviolation", function (event) {
  window.__cspViolations.push(
    event.effectiveDirective + " blocked " + (event.blockedURI || "inline") +
    (event.sourceFile ? " from " + event.sourceFile.replace(/^https?:\\/\\/[^/]+/, "") : "")
  );
});
"""


def watch(context: Any) -> dict[str, list[str]]:
    """Record dialogs, console errors and page errors for every page."""
    seen: dict[str, list[str]] = {"dialogs": [], "console": [], "errors": []}
    context.add_init_script(CSP_INIT_SCRIPT)

    def on_page(page: Any) -> None:
        def on_dialog(dialog: Any) -> None:
            seen["dialogs"].append(dialog.message)
            dialog.dismiss()

        def on_console(message: Any) -> None:
            if message.type == "error":
                seen["console"].append(message.text)

        page.on("dialog", on_dialog)
        page.on("console", on_console)
        page.on("pageerror", lambda error: seen["errors"].append(str(error)))

    context.on("page", on_page)
    return seen


def csp_events(page: Any) -> list[str]:
    return page.evaluate("() => window.__cspViolations.slice()")


def finish(failures: list[str]) -> int:
    """Print the verdict line every proof ends with and return its exit code."""
    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


def main_guard(main) -> None:
    sys.exit(main())


# What the slice shows, read through its `data-*` test hooks only, so the
# proofs do not depend on layout.  Text is the node's exact `textContent`.
# `visible` means: laid out with a size, not hidden, and wholly inside the
# viewport's width (so nothing needs a sideways scroll to be seen).
READ_SLICE_JS = """
() => {
  const width = document.documentElement.clientWidth;
  const shown = (node) => {
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 && style.visibility !== "hidden" &&
      box.left >= -0.5 && box.right <= width + 0.5;
  };
  const cell = (node) => node === null ? null : ({
    text: node.textContent.trim(),
    unknown: node.matches("[data-unknown]") || node.querySelector("[data-unknown]") !== null,
    visible: shown(node),
  });
  const cells = (root, attribute) => Object.fromEntries(
    Array.from(root.querySelectorAll("[" + attribute + "]")).map(
      (node) => [node.getAttribute(attribute), cell(node)]));
  const own = (root, selector, inside) => Array.from(root.querySelectorAll(selector))
    .filter((node) => node.closest(inside) === root);
  return {
    status: document.getElementById("vc-status").textContent.trim(),
    connection: document.getElementById("vc-status").getAttribute("data-connection"),
    reconciliation: document.getElementById("vc-reconciliation").textContent.trim(),
    scope: document.getElementById("vc-scope").textContent.trim(),
    session: cell(document.querySelector("[data-field=session_note]")),
    sections: Array.from(document.querySelectorAll("[data-section]")).map((n) => n.getAttribute("data-section")),
    empty: Array.from(document.querySelectorAll("[data-empty]")).map((n) => n.getAttribute("data-empty")),
    kinds: Array.from(document.querySelectorAll("[data-kind-filter]")).map((n) => ({
      value: n.getAttribute("data-kind-filter"), text: n.textContent.trim(),
      pressed: n.getAttribute("aria-pressed") })),
    facets: Object.fromEntries(Array.from(document.querySelectorAll("select[data-facet]")).map((n) => [
      n.getAttribute("data-facet"),
      { selected: n.value, options: Array.from(n.options).map((o) => o.value + "=" + o.textContent.trim()) },
    ])),
    groups: Array.from(document.querySelectorAll("article[data-group]")).map((article) => ({
      key: article.getAttribute("data-group"),
      kind: article.getAttribute("data-kind"),
      fields: Object.fromEntries(own(article, "[data-field]", "article, [data-member], [data-stat]")
        .map((node) => [node.getAttribute("data-field"), cell(node)])),
      shared: cells(article, "data-shared"),
      stats: Object.fromEntries(Array.from(article.querySelectorAll("[data-stat]")).map((node) => [
        node.getAttribute("data-stat"),
        { value: node.querySelector("[data-field=stat_value]").textContent.trim(),
          role: (node.querySelector("[data-field=stat_role]") || { textContent: "" }).textContent.trim(),
          visible: shown(node) },
      ])),
      members: Array.from(article.querySelectorAll("[data-member]")).map((row) => ({
        id: row.getAttribute("data-member"),
        fields: cells(row, "data-field"),
        buttons: Array.from(row.querySelectorAll("button")).map((button) => ({
          label: button.textContent.trim(), name: button.getAttribute("aria-label"),
          pressed: button.getAttribute("aria-pressed"),
          disabled: button.disabled || button.getAttribute("aria-disabled") === "true",
          visible: shown(button) })),
      })),
    })),
  };
}
"""


def read_slice(page: Any) -> dict:
    return page.evaluate(READ_SLICE_JS)


def two_class_fixture() -> bytes:
    """``armor_close.csv`` with its same-stat pair re-classed, in memory.

    The exact group stays Titan and the same-stat group becomes Hunter, so a
    Class selection can be one that the other kind lacks.
    """
    lines = (FIXTURES / "armor_close.csv").read_bytes().split(b"\n")
    changed = [
        line.replace(b",Titan,", b",Hunter,", 1) if line.startswith(b"Tuning Twin,") else line
        for line in lines
    ]
    return b"\n".join(changed)


def member(page: Any, member_id: str) -> dict:
    """One member's verdict presentation, wherever it is on the page."""
    for group in read_slice(page)["groups"]:
        for row in group["members"]:
            if row["id"] == member_id:
                return {
                    "verdict": row["fields"].get("verdict", {}).get("text"),
                    "persisted_veto": "persisted_veto" in row["fields"],
                    "pressed": [b["label"] for b in row["buttons"] if b["pressed"] == "true"],
                    "disabled": [b["disabled"] for b in row["buttons"]],
                }
    return {}


def verdict_button(page: Any, member_id: str, label: str) -> Any:
    """Found by accessible name, which carries the member's id."""
    return page.get_by_role("button", name=f"{label} item {member_id}", exact=True)


def status(page: Any) -> str:
    return page.locator("#vc-status").text_content().strip()


def wait_status(page: Any, fragment: str) -> None:
    page.wait_for_function(
        "text => document.getElementById('vc-status').textContent.includes(text)", arg=fragment
    )
