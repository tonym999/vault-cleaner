"""Gate D: byte-identical PNG pairs, #206 beside #209 in one authenticated run.

Only fixed baseline assets are substituted through Playwright routing; both
pages fetch the same report from the unmodified server. Captures stay in
memory. Four width/scheme idle pairs and one held-request pair are compared.
No Python image dependency, no screenshot written into frozen evidence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from run_proof import configure

configure()
from dev import preload
from harness import authenticated_context, chromium, finish, live_spike
from proof_s5_focus import hold_one

BASELINE = Path(__file__).resolve().parents[1] / "issue-206" / "frontend" / "dist"


def baseline_assets(page) -> None:
    def serve(route):
        name = route.request.url.rsplit("/", 1)[-1]
        route.fulfill(body=(BASELINE / "assets" / name).read_bytes(),
                      content_type="text/css" if name.endswith("css") else "text/javascript")
    page.route("**/spike/assets/*", serve)


def capture(page, width: int) -> bytes:
    page.mouse.move(0, 0)
    page.evaluate("() => { document.activeElement.blur(); window.scrollTo(0, 0); }")
    page.wait_for_timeout(300)
    return page.screenshot(full_page=True, clip={"x": 0, "y": 0, "width": width, "height": 2400})


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        preload(live, "real")
        context = authenticated_context(browser, live)
        for width in (1440, 390):
            for scheme in ("light", "dark"):
                images = []
                for baseline in (True, False):
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": 900})
                    page.emulate_media(color_scheme=scheme)
                    if baseline:
                        baseline_assets(page)
                    page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
                    page.wait_for_selector("article[data-group]")
                    images.append(capture(page, width))
                    page.close()
                equal = images[0] == images[1]
                print(f"idle {width}px {scheme}: #206={len(images[0])} bytes #209={len(images[1])} bytes; "
                      f"top 2400px PNG identical={equal}")
                if not equal:
                    failures.append(f"idle {width}px {scheme} differs")
        pages = [context.new_page(), context.new_page()]
        baseline_assets(pages[0])
        held = []
        for page in pages:
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
            page.wait_for_selector("article[data-group]")
            held.append(hold_one(page))
        images = []
        for page, pending in zip(pages, held, strict=True):
            page.locator('[data-member] button').first.focus()
            page.keyboard.press("Enter")
            while not pending:
                page.wait_for_timeout(20)
            assert page.locator('[data-member] button[aria-disabled="false"]').count() == 0
            images.append(capture(page, 1440))
        equal = images[0] == images[1]
        print(f"in-flight 1440px light: #206={len(images[0])} bytes #209={len(images[1])} bytes; "
              f"all 435 verdict controls aria-disabled; top 2400px PNG identical={equal}")
        if not equal:
            failures.append("in-flight state differs")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    sys.exit(main())
