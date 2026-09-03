"""Measure the issue #113 narrow count-treatment specimens at 390x844.

The narrow comparison in ``docs/duplicate-review-count-design.md`` cites block
heights for the two count treatments. Those numbers are produced here rather
than by eye, because three earlier attempts at them were wrong in three
different ways:

* a box given ``width: 390px`` inside a desktop document activates no narrow
  media query and sits in the wrong layout context;
* measuring inside ``count-treatments.html`` at a real 390px viewport leaves
  the specimen 241px wide once that document's own padding is taken;
* and one revision omitted Alternative A's tile row entirely, which is not a
  measurement error but a comparison of two different things.

So this script asserts its preconditions before it reports anything: the
viewport really is 390px, the document does not scroll sideways, the panels sit
at the production width, and both specimens carry a tile row.

Usage (from the repo root, with the project venv):

    .venv/bin/python scripts/measure_narrow_specimens.py [--write-screenshots]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "docs" / "evidence" / "issue-113" / "narrow-390-specimens.html"
OUT = HARNESS.parent
VIEWPORT = {"width": 390, "height": 844}

# review.css:166 drops .wrap padding to .6rem at <=640px, so a panel spans
# 390 - 2*9.6 = 370.8. Asserting this is what catches a harness that is not
# actually sitting in the production layout.
EXPECTED_PANEL_WIDTH = 370.8

PROBE = """() => {
  const panel = id => {
    const e = document.getElementById(id);
    const r = e.getBoundingClientRect();
    const part = sel => {
      const p = e.querySelector(sel);
      return p ? Math.round(p.getBoundingClientRect().height) : null;
    };
    return {
      width: +r.width.toFixed(1),
      height: Math.round(r.height),
      overflows: e.scrollWidth > e.clientWidth + 1,
      tiles: part('.tiles'),
      tileCount: e.querySelectorAll('.tile').length,
      chips: part('.chips'),
      scope: part('.scope'),
      group: part('.grp'),
    };
  };
  return {
    innerWidth: window.innerWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    a: panel('narrow-a'),
    b: panel('narrow-b'),
  };
}"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-screenshots",
        action="store_true",
        help="regenerate narrow-390-alternative-{a,b}.png alongside the harness",
    )
    args = parser.parse_args()

    if not HARNESS.exists():
        print(f"missing harness: {HARNESS}", file=sys.stderr)
        return 1

    remote: list[str] = []
    with sync_playwright() as play:
        browser = play.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = context.new_page()
        page.on(
            "request",
            lambda r: remote.append(r.url) if not r.url.startswith("file://") else None,
        )
        page.goto(HARNESS.resolve().as_uri(), wait_until="load")
        page.wait_for_timeout(300)
        result = page.evaluate(PROBE)
        if args.write_screenshots:
            page.locator("#narrow-a").screenshot(
                path=str(OUT / "narrow-390-alternative-a.png")
            )
            page.locator("#narrow-b").screenshot(
                path=str(OUT / "narrow-390-alternative-b.png")
            )
        browser.close()

    a, b = result["a"], result["b"]
    failures: list[str] = []

    if result["innerWidth"] != VIEWPORT["width"]:
        failures.append(f"viewport is {result['innerWidth']}px, expected 390")
    if result["docScrollWidth"] > result["clientWidth"] + 1:
        failures.append(
            f"document scrolls sideways: {result['docScrollWidth']}px "
            f"in {result['clientWidth']}px"
        )
    for name, panel in (("A", a), ("B", b)):
        if abs(panel["width"] - EXPECTED_PANEL_WIDTH) > 0.5:
            failures.append(
                f"{name} panel is {panel['width']}px, expected "
                f"{EXPECTED_PANEL_WIDTH}px at the production width"
            )
        if panel["overflows"]:
            failures.append(f"{name} overflows its panel")
        # Both treatments keep a tile row: A deletes only the SHOWN tile.
        if panel["tileCount"] != 4:
            failures.append(
                f"{name} has {panel['tileCount']} tiles, expected 4 — the "
                "treatments must be compared with equivalent content"
            )
    if remote:
        failures.append(f"harness made remote requests: {remote}")

    print(f"viewport            {result['innerWidth']}x{VIEWPORT['height']}")
    print(f"document scrollWidth {result['docScrollWidth']} (client {result['clientWidth']})")
    for name, panel in (("A · scoped summary line", a), ("B · distributed counts", b)):
        print(f"\n{name}")
        print(f"  panel width   {panel['width']}px")
        print(f"  block height  {panel['height']}px")
        print(f"  tiles         {panel['tiles']}px across {panel['tileCount']} tiles")
        print(f"  chips         {panel['chips']}px")
        print(f"  scope line    {panel['scope']}px" if panel["scope"] else "  scope line    n/a")
        print(f"  group header  {panel['group']}px")

    if failures:
        print("\nFAILED preconditions:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nAll preconditions hold; heights above are citable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
