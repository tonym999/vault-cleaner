"""S6: layouts (gate H5, contract section 8).

At 1440, 1024 and 390 px, in the light and the dark scheme, for a report
with both kinds of group and for the four-member group:

* the page does not scroll sideways, and no element inside a group scrolls
  sideways either, so members are compared without horizontal navigation;
* every member's id and every value that differs is inside the viewport;
* ids and hashes wrap: none is clipped or ellipsised;
* Tab reaches every control, in document order, and every tab stop is
  visible (no hidden duplicate control is in the tab order).

    .venv/bin/python spikes/issue-206/proof_s6_layout.py
    .venv/bin/python spikes/issue-206/proof_s6_layout.py --screenshots

``--screenshots`` also writes the PNG files under ``docs/evidence/issue-206/``.
"""

from __future__ import annotations

import sys
from typing import Any

from expected import compare
from harness import (
    REPO,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_slice,
    read_slice,
    report,
    upload,
    verdict_button,
    wait_status,
)

EVIDENCE = REPO / "docs" / "evidence" / "issue-206"
WIDTHS = (1440, 1024, 390)
SCHEMES = ("light", "dark")
SHOTS = {(1440, "light"): "desktop-light", (1440, "dark"): "desktop-dark",
         (390, "light"): "narrow-light", (390, "dark"): "narrow-dark"}
LAYOUT_JS = """
() => {
  const width = document.documentElement.clientWidth;
  const inside = (node) => {
    const box = node.getBoundingClientRect();
    return box.width > 0 && box.left >= -0.5 && box.right <= width + 0.5;
  };
  const scrollers = Array.from(document.querySelectorAll("main *")).filter((node) => {
    const overflow = getComputedStyle(node).overflowX;
    return (overflow === "auto" || overflow === "scroll") && node.scrollWidth > node.clientWidth;
  }).length;
  const opaque = Array.from(document.querySelectorAll("[data-field=id], [data-field=hash]"));
  const controls = Array.from(document.querySelectorAll("a[href], button, select, input"))
    .filter((node) => node.tabIndex >= 0 && !node.disabled);
  const rows = Array.from(document.querySelectorAll("[data-member]"));
  return {
    sideways: document.documentElement.scrollWidth > width,
    scrollers: scrollers,
    opaqueInside: opaque.every(inside),
    opaqueClipped: opaque.filter((node) => {
      const style = getComputedStyle(node);
      return style.textOverflow === "ellipsis" || node.scrollWidth > node.clientWidth + 1;
    }).length,
    controls: controls.length,
    hiddenControls: controls.filter((node) => !node.matches("a[href='#vc-title']") && !inside(node)).length,
    memberColumns: new Set(rows.map((row) => Math.round(row.getBoundingClientRect().left))).size,
  };
}
"""
FOCUS_JS = """
() => {
  const node = document.activeElement;
  const box = node.getBoundingClientRect();
  return {
    name: node.getAttribute("aria-label") || node.textContent.trim().replace(/\\s+/g, " ") ||
      node.getAttribute("data-facet") || node.id,
    visible: box.width > 0 && box.height > 0,
    order: Array.from(document.querySelectorAll("a[href], button, select, input")).indexOf(node),
  };
}
"""


def tab_through(page: Any) -> list[dict]:
    """Press Tab until the cycle repeats; return one lap, from the first control."""
    stops: list[dict] = []
    # One lap plus the body stop and a margin, including large reports (S15).
    limit = page.locator("a[href], button, select, input").count() + 5
    for _ in range(limit):
        page.keyboard.press("Tab")
        stop = page.evaluate(FOCUS_JS)
        if stop["order"] == -1:
            continue
        if stops and stop["order"] == stops[0]["order"]:
            break
        stops.append(stop)
    start = next((index for index, stop in enumerate(stops) if stop["order"] == 0), 0)
    return stops[start:] + stops[:start]


def main() -> int:
    write = sys.argv[1:] == ["--screenshots"]
    failures: list[str] = []
    with chromium() as browser:
        for fixture, tag in (("armor_close.csv", "both-kinds"), ("armor_same_stat_four_ui.csv", "four-members")):
            print(f"-- {fixture} --")
            with live_spike() as live:
                context = authenticated_context(browser, live)
                upload(context, live, fixture)
                first = "6032" if tag == "both-kinds" else "8402"
                page = open_slice(context, live)
                verdict_button(page, first, "Veto").click()
                wait_status(page, "recorded your veto")
                envelope = report(context, live)
                for width in WIDTHS:
                    for scheme in SCHEMES:
                        page.set_viewport_size({"width": width, "height": 900})
                        page.emulate_media(color_scheme=scheme)
                        layout = page.evaluate(LAYOUT_JS)
                        problems = compare(read_slice(page), envelope)
                        stops = tab_through(page)
                        in_order = [stop["order"] for stop in stops] == list(range(len(stops)))
                        print(f"{width}px {scheme}: page scrolls sideways={layout['sideways']}; "
                              f"sideways scrollers inside the page={layout['scrollers']}; "
                              f"every required value visible={not problems}; "
                              f"ids and hashes inside the viewport={layout['opaqueInside']}, clipped={layout['opaqueClipped']}; "
                              f"members stacked in {layout['memberColumns']} column; "
                              f"controls={layout['controls']}, reached by Tab in document order={len(stops)} "
                              f"({in_order}), tab stops not visible={sum(not s['visible'] for s in stops)}, "
                              f"controls outside the viewport={layout['hiddenControls']}")
                        if (
                            layout["sideways"] or layout["scrollers"] or problems
                            or not layout["opaqueInside"] or layout["opaqueClipped"]
                            or len(stops) != layout["controls"] or not in_order
                            or not all(stop["visible"] for stop in stops) or layout["hiddenControls"]
                            or layout["memberColumns"] != 1
                        ):
                            failures.append(f"{fixture} at {width}px {scheme}")
                            failures.extend(problems[:2])
                        if write and (width, scheme) in SHOTS and (tag == "both-kinds" or scheme == "light"):
                            page.evaluate("() => { document.activeElement.blur(); window.scrollTo(0, 0); }")
                            name = f"{tag}-{SHOTS[(width, scheme)]}.png"
                            EVIDENCE.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(EVIDENCE / name), full_page=True)
                            print(f"  wrote docs/evidence/issue-206/{name}")
                if tag == "both-kinds":
                    page.set_viewport_size({"width": 390, "height": 900})
                    print(f"tab order at 390px: {[stop['name'] for stop in tab_through(page)]}")
                context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
