"""Shared plumbing for the #137 proof scripts.

Every proof boots the spike app (the production app plus the spike routes)
on a loopback port, with fake fixtures only.  Browser proofs use the pinned
Playwright Chromium and stop with an error when it is missing; they never
skip.
"""

from __future__ import annotations

import logging
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from spike_app import EnvelopeTransform, build_spike_server

from vault_cleaner.server import app as server_app
from vault_cleaner.server.session import Session

SPIKE_DIR = Path(__file__).resolve().parent
REPO = SPIKE_DIR.parents[1]
FIXTURES = REPO / "tests" / "fixtures"
SLICE_FIXTURES = (
    "armor_close.csv",
    "armor_duplicates_ui.csv",
    "armor_same_stat_ui.csv",
    "armor_same_stat_four_ui.csv",
)
STATUS_REGIONS = ("vc-status", "vc-reconciliation", "vc-duplicate-scope")


# Request logs carry the port and a timestamp; keep proof output repeatable.
logging.getLogger("werkzeug").setLevel(logging.ERROR)


@dataclass(frozen=True)
class LiveSpike:
    session: Session
    origin: str
    bootstrap_url: str
    server: Any


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


@contextmanager
def live_spike(
    transform_envelope: EnvelopeTransform | None = None,
) -> Iterator[LiveSpike]:
    """Serve the spike app from a thread until the block exits."""
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-137-") as raw:
        root = Path(raw)
        staging = root / "staging"
        staging.mkdir()
        config = root / "config.toml"
        config.write_text("", encoding="utf-8")
        original = server_app.tempfile
        server_app.tempfile = _StagingTempfile(staging)
        session = Session(
            overrides_path=str(root / "overrides.json"),
            config_path=str(config),
            no_wishlists=True,
            bootstrap_token="spike-bootstrap",
            session_token="spike-session",
        )
        server = build_spike_server(session, 0, transform_envelope=transform_envelope)
        thread = threading.Thread(target=server.serve_forever, name="spike-137-server")
        thread.start()
        origin = session.expected_origin
        try:
            yield LiveSpike(
                session=session,
                origin=origin,
                bootstrap_url=f"{origin}/bootstrap?token={session.bootstrap_token}",
                server=server,
            )
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            session.close()
            server_app.tempfile = original


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


def authenticated_context(browser: Any, live: LiveSpike, width: int = 1440, height: int = 1000):
    """A browser context that has completed the real bootstrap exchange."""
    context = browser.new_context(viewport={"width": width, "height": height})
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


def open_spike(context: Any, live: LiveSpike, query: str = "") -> Any:
    page = context.new_page()
    page.goto(f"{live.origin}/spike/{query}", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => /Connected|failed/.test(document.getElementById('vc-status').textContent)"
    )
    return page


def open_production_duplicates(context: Any, live: LiveSpike) -> Any:
    """The production page with its Armor duplicates surface selected."""
    page = context.new_page()
    page.goto(f"{live.origin}/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => /Connected/.test(document.getElementById('vc-status').textContent)"
    )
    page.locator("#vc-view-duplicates").click()
    return page


# A normalised projection of one subtree: every element's tag and attributes
# (sorted), every non-blank text node exactly, and each button's live
# `disabled` property.  Whitespace-only text nodes are layout, not content.
PROJECT_JS = """
root => {
  function project(node) {
    if (node.nodeType === 3) {
      return /^\\s*$/.test(node.data) ? null : { text: node.data };
    }
    if (node.nodeType !== 1) return null;
    var attributes = {};
    Array.prototype.slice.call(node.attributes).forEach(function (attribute) {
      attributes[attribute.name] = attribute.value;
    });
    var entry = { tag: node.nodeName.toLowerCase(), attributes: attributes, children: [] };
    if (entry.tag === "button") entry.disabled = node.disabled;
    Array.prototype.slice.call(node.childNodes).forEach(function (child) {
      var projected = project(child);
      if (projected) entry.children.push(projected);
    });
    return entry;
  }
  return project(root);
}
"""


def project(page: Any, selector: str = "#vc-duplicate-list") -> dict:
    return page.locator(selector).evaluate(PROJECT_JS)


def walk(node: dict) -> Iterator[dict]:
    yield node
    for child in node.get("children", []):
        yield from walk(child)


CSP_INIT_SCRIPT = """
window.__cspViolations = [];
document.addEventListener("securitypolicyviolation", function (event) {
  window.__cspViolations.push(event.effectiveDirective);
});
"""


def watch(context: Any) -> dict[str, list[str]]:
    """Record dialogs and CSP console messages for every page of a context."""
    seen: dict[str, list[str]] = {"dialogs": [], "csp_console": []}
    context.add_init_script(CSP_INIT_SCRIPT)

    def on_page(page: Any) -> None:
        def on_dialog(dialog: Any) -> None:
            seen["dialogs"].append(dialog.message)
            dialog.dismiss()

        def on_console(message: Any) -> None:
            if "Content Security Policy" in message.text:
                seen["csp_console"].append(message.text)

        page.on("dialog", on_dialog)
        page.on("console", on_console)

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
