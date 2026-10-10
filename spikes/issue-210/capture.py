"""Capture the #210 slice for the owner's review.

    .venv/bin/python spikes/issue-210/capture.py OUT_DIR [real|synthetic]

Serves the built #210 frontend from the unmodified review server (through the
#206 harness), uploads a fixed tracked fixture, and writes PNG captures in
dark and light at 1440 px and 390 px. Nothing under ``data/`` is read.
"""

from __future__ import annotations

import sys
from pathlib import Path

from run_proof import configure

configure()

import harness
from dev import preload

WIDTHS = {"desktop": (1440, 1000, 1), "narrow": (390, 844, 2)}
# A sticky heading would be painted over the middle of a tall capture, so it
# is pinned for the still image. Through the CSSOM: the server's policy
# refuses an injected style element.
STILL = "document.querySelectorAll('.kind-head').forEach((head) => { head.style.position = 'static'; })"


def group_with(page, pieces: int):
    return page.locator(f"article[data-group]:has(.n{pieces})").first


def signed_in(browser, live) -> dict:
    """The session cookie from one real bootstrap; the sign-in link is one-use."""
    context = harness.authenticated_context(browser, live)
    state = context.storage_state()
    context.close()
    return state


def capture_real(browser, live, out: Path) -> None:
    state = signed_in(browser, live)
    for scheme in ("dark", "light"):
        for name, (width, height, scale) in WIDTHS.items():
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=scale,
                color_scheme=scheme,
                storage_state=state,
            )
            page = context.new_page()
            page.goto(f"{live.origin}/spike/")
            page.wait_for_selector("article[data-group]")
            stem = f"real-{name}-{scheme}"
            total = page.evaluate("document.documentElement.scrollHeight")
            wide = page.evaluate("document.documentElement.scrollWidth")
            print(f"{stem}: page {wide} x {total} px, {page.locator('article[data-group]').count()} groups")
            page.screenshot(path=out / f"{stem}-viewport.png")
            page.evaluate(STILL)
            tall = 1900 if name == "desktop" else 2300
            page.screenshot(path=out / f"{stem}-top.png", full_page=True,
                            clip={"x": 0, "y": 0, "width": width, "height": tall})
            edge = page.evaluate(
                "document.querySelector('.kind-same_stat').getBoundingClientRect().top + scrollY")
            page.screenshot(path=out / f"{stem}-boundary.png", full_page=True,
                            clip={"x": 0, "y": max(0, edge - tall * 0.3), "width": width, "height": tall})
            group_with(page, 3).screenshot(path=out / f"{stem}-three.png")
            group_with(page, 4).screenshot(path=out / f"{stem}-four.png")
            context.close()


def capture_synthetic(browser, live, out: Path, fixture: str, stem: str) -> None:
    state = signed_in(browser, live)
    for name, (width, height, scale) in WIDTHS.items():
        context = browser.new_context(
            viewport={"width": width, "height": height}, device_scale_factor=scale,
            color_scheme="dark", storage_state=state,
        )
        page = context.new_page()
        page.goto(f"{live.origin}/spike/")
        page.wait_for_selector("article[data-group]")
        page.evaluate(STILL)
        page.screenshot(path=out / f"{stem}-{name}-dark.png", full_page=True)
        context.close()


def main() -> int:
    if len(sys.argv) not in (2, 3) or (len(sys.argv) == 3 and sys.argv[2] not in ("real", "synthetic")):
        print(__doc__)
        return 1
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    which = sys.argv[2] if len(sys.argv) == 3 else "real"
    harness.require_build()
    with harness.chromium() as browser:
        if which == "real":
            with harness.live_spike() as live:
                preload(live, "real")
                capture_real(browser, live, out)
        else:
            for fixture, stem in (("armor_close.csv", "both-kinds"),
                                  ("armor_same_stat_four_ui.csv", "four-members")):
                with harness.live_spike() as live:
                    preload(live, fixture)
                    capture_synthetic(browser, live, out, fixture, stem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
