"""#210: accessibility and focus, in place of #206's S13 (plan Amendment 1).

    .venv/bin/python spikes/issue-210/proof_axe.py

S13 cannot run on this slice: it prints the lowest ratio among the nodes axe
could not judge and crashes when there are none, and its negative control
depends on daisyUI's ``btn-primary`` class and cascade. This proof reuses,
unedited, S13's axe script (``RUN_JS``) and ``focus_contrast.check``, covers
S13's seven states at 1440 px and 390 px in both schemes, and adds the
tracked sanitised fixture.

A state fails on any axe violation, any node axe leaves unjudged, any
measured ratio under 4.5:1, a background image on anything but the native
select, and any focus stop that misses the 3 px outline, its 2 px offset or
3:1. Differences from S13, each required by the plan:

- nothing left unjudged is a pass, not a crash;
- before each axe run the page is scrolled to the top and focus is cleared,
  so the previous keyboard lap cannot leave a sticky heading over a node;
- **no focus outline is clipped** (Amendment 2): on a real keyboard lap in
  each direction, every stop's painted outline lies inside the viewport on
  all four sides, clear of the sticky heading, and inside every ancestor
  that clips. Computed style alone is not enough: that is how a clipped
  outline was first reported as present. The first version of this check
  compared only the viewport's sides and passed outlines that ran off its
  bottom (second review of #210, REV-01);
- five negative controls of its own, each applied through the CSSOM and each
  required to be detected.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from run_proof import configure

configure()

import harness
from dev import preload
from focus_contrast import SETTLE_JS, check, keyboard_lap, problems
from proof_s5_focus import hold_one
from proof_s13_axe import AXE, RUN_JS

SIZES = ((1440, "light"), (1440, "dark"), (390, "light"), (390, "dark"))
REST_JS = "() => { if (document.activeElement) document.activeElement.blur(); window.scrollTo(0, 0); }"

# The focused control, measured after a real key press, so the browser is in
# keyboard modality and has scrolled the control into view its own way.  The
# outline is painted outside the border box by its width plus its offset.  It
# must lie inside the viewport on all four sides, clear of any sticky or
# fixed element that is not its own ancestor, and inside every ancestor that
# clips (a non-visible overflow on an axis, paint containment or a clip
# path; the clipping edge is the ancestor's padding box).
FOCUSED_JS = """
() => {
  const node = document.activeElement;
  if (!node || node === document.body) return null;
  const name = node.getAttribute("aria-label") || node.textContent.trim().replace(/\\s+/g, " ");
  const stop = window.__stops.indexOf(node);
  if (!node.matches(":focus-visible")) return { stop, name, visible: false, cut: "" };
  const style = getComputedStyle(node);
  const grow = parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset);
  const box = node.getBoundingClientRect();
  const ring = { left: box.left - grow, right: box.right + grow, top: box.top - grow, bottom: box.bottom + grow };
  const width = document.documentElement.clientWidth;
  const height = document.documentElement.clientHeight;
  if (ring.left < -0.5 || ring.right > width + 0.5) return { stop, name, visible: true, cut: "the viewport's side" };
  if (ring.top < -0.5) return { stop, name, visible: true, cut: "the viewport's top" };
  if (ring.bottom > height + 0.5) return { stop, name, visible: true, cut: "the viewport's bottom" };
  for (const over of window.__covers) {
    const position = getComputedStyle(over).position;
    if (over.contains(node)) continue;
    const cover = over.getBoundingClientRect();
    if (cover.width > 0 && cover.height > 0 && ring.left < cover.right && ring.right > cover.left
        && ring.top < cover.bottom - 0.5 && ring.bottom > cover.top + 0.5) {
      return { stop, name, visible: true, cut: "a " + position + " " + over.tagName.toLowerCase() + "." + over.className.split(" ")[0] };
    }
  }
  for (let at = node.parentElement; at; at = at.parentElement) {
    const around = getComputedStyle(at);
    const x = around.overflowX !== "visible";
    const y = around.overflowY !== "visible";
    const paint = /paint|strict|content/.test(around.contain) || around.clipPath !== "none";
    if (!x && !y && !paint) continue;
    const outer = at.getBoundingClientRect();
    const edge = {
      left: outer.left + parseFloat(around.borderLeftWidth),
      right: outer.right - parseFloat(around.borderRightWidth),
      top: outer.top + parseFloat(around.borderTopWidth),
      bottom: outer.bottom - parseFloat(around.borderBottomWidth),
    };
    const cutX = (x || paint) && (ring.left < edge.left - 0.5 || ring.right > edge.right + 0.5);
    const cutY = (y || paint) && (ring.top < edge.top - 0.5 || ring.bottom > edge.bottom + 0.5);
    if (cutX || cutY) return { stop, name, visible: true, cut: "its ancestor " + at.tagName.toLowerCase() + "." + at.className.split(" ")[0] };
  }
  return { stop, name, visible: true, cut: "" };
}
"""
# Before a lap: the sticky and fixed elements, found once, and the stop count.
STOPS_JS = """
() => {
  window.__covers = Array.from(document.querySelectorAll("*")).filter((node) => {
    const position = getComputedStyle(node).position;
    return position === "sticky" || position === "fixed";
  });
  window.__stops = Array.from(document.querySelectorAll("a[href], button, select, input"));
  return window.__stops.length;
}
"""
ADD_RULE_JS = """(rule) => {
  const sheet = document.styleSheets[0];
  window.__added = sheet.insertRule(rule, sheet.cssRules.length);
}"""
DROP_RULE_JS = "() => { document.styleSheets[0].deleteRule(window.__added); delete window.__added; }"
# focus_contrast.negative_control's own way of swapping the unlayered floor,
# with a low-contrast colour in place of daisyUI's layered rule.
WEAK_FOCUS_JS = """() => {
  for (const sheet of document.styleSheets) {
    const index = Array.from(sheet.cssRules).findIndex((rule) => rule.selectorText === ":focus-visible");
    if (index === -1) continue;
    const saved = sheet.cssRules[index].cssText;
    sheet.deleteRule(index);
    sheet.insertRule(":focus-visible { outline: 3px solid var(--card); outline-offset: 2px; }", index);
    window.__restoreFocusFloor = () => { sheet.deleteRule(index); sheet.insertRule(saved, index); };
    return;
  }
  throw new Error("unlayered focus floor not found");
}"""


def size(page: Any, width: int, scheme: str) -> None:
    page.set_viewport_size({"width": width, "height": 900})
    page.emulate_media(color_scheme=scheme)
    page.mouse.move(0, 0)
    page.evaluate(REST_JS)
    # A theme change may transition colours; measure settled styles.
    page.evaluate(SETTLE_JS)


def axe(page: Any) -> dict:
    return page.evaluate(RUN_JS)


def unexplained(result: dict) -> list[str]:
    """What S13 fails a state on, without its assumption that something is unjudged."""
    found = [f"violation {entry}" for entry in result["violations"]]
    found += [f"not judged: {target}" for target in result["unmeasured"]]
    found += [f"{entry['target']} at {entry['ratio']:.2f}:1" for entry in result["measured"]
              if entry["ratio"] < 4.5]
    found += [f"background image on {entry['target']}" for entry in result["measured"]
              if not entry["plain"] and entry["target"] != "select"]
    return found


def clipping(page: Any, backward: bool = False) -> dict:
    """One real keyboard lap, Tab or Shift+Tab, measuring each stop as it takes focus.

    Forward, the browser brings a control in at the bottom of the viewport;
    backward, at the top, under the sticky heading. Both are walked.
    """
    page.evaluate(REST_JS)
    if backward:
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
    stops = page.evaluate(STOPS_JS)
    key = "Shift+Tab" if backward else "Tab"
    # The lap does not start at a known stop (the browser keeps its place
    # after a blur) and passes through the document's edge once, where
    # nothing in the page has focus. So walk until every stop has been seen,
    # with a few presses to spare, and count stops, not presses.
    seen: dict[int, dict] = {}
    for _ in range(stops + 3):
        page.keyboard.press(key)
        focused = page.evaluate(FOCUSED_JS)
        if focused is not None and focused["stop"] >= 0:
            seen.setdefault(focused["stop"], focused)
        if len(seen) == stops:
            break
    page.evaluate(REST_JS)
    return {
        "stops": stops,
        "reached": len(seen),
        "visible": sum(entry["visible"] for entry in seen.values()),
        "clipped": [f"{entry['name']} by {entry['cut']}" for entry in seen.values() if entry["cut"]],
    }


def clipping_both(page: Any, label: str, failures: list[str]) -> None:
    for backward in (False, True):
        ring = clipping(page, backward)
        way = "Shift+Tab" if backward else "Tab"
        print(f"{label}, {way}: focus stops={ring['stops']}, reached={ring['reached']}, with a visible "
              f"focus indicator={ring['visible']}, outline clipped or covered={len(ring['clipped'])} "
              f"{ring['clipped'][:3]}")
        if ring["reached"] != ring["stops"] or ring["visible"] != ring["stops"] or ring["clipped"]:
            failures.append(f"{label}, {way}: a focus outline is clipped, covered or missing")


def run(page: Any, label: str, failures: list[str]) -> None:
    """One state at both widths and schemes. Also S15's accessibility step."""
    for width, scheme in SIZES:
        size(page, width, scheme)
        result = axe(page)
        bad = unexplained(result)
        ratios = [entry["ratio"] for entry in result["measured"]]
        lowest = f"{min(ratios):.2f}:1" if ratios else "none to measure"
        print(f"{label}, {width}px {scheme}: rules passed={result['passes']}, "
              f"violations={result['violations']}; contrast axe could not judge: "
              f"{result['incomplete']} nodes, measured here {len(ratios)}, lowest {lowest}; "
              f"unexplained: {bad}")
        if bad:
            failures.append(f"{label}, {width}px {scheme}: an accessibility problem is unexplained")
        check(page, f"{label}, {width}px {scheme}", failures)
        clipping_both(page, f"{label}, {width}px {scheme}", failures)


def negative_controls(page: Any, failures: list[str]) -> None:
    """Each control breaks one thing through the CSSOM; the checks must see it."""
    size(page, 390, "dark")
    # 1. The defect the first diagnostic found: a muted role word on a filled stat cell.
    page.evaluate(ADD_RULE_JS, ".stat[data-role] .stat-role { color: var(--muted-foreground) !important; }")
    seen = unexplained(axe(page))
    page.evaluate(DROP_RULE_JS)
    print(f"negative control, muted role word on a filled stat cell (390px dark): detected={bool(seen)} "
          f"{seen[:1]}")
    if not seen:
        failures.append("negative control: a contrast failure was not detected")
    # 2. A focus outline that does not contrast with the surface behind it.
    page.evaluate(WEAK_FOCUS_JS)
    weak = problems(keyboard_lap(page))
    page.evaluate("() => { window.__restoreFocusFloor(); delete window.__restoreFocusFloor; }")
    print(f"negative control, focus outline in the card colour: controls failing={len(weak)}")
    if not weak:
        failures.append("negative control: a low-contrast focus outline was not detected")
    # 3. The first reviewed defect: the joined-button wrapper clips its buttons' outlines.
    size(page, 1440, "dark")
    page.evaluate(ADD_RULE_JS, ".verdict { overflow: hidden; }")
    ring = clipping(page)
    page.evaluate(DROP_RULE_JS)
    verdicts = page.locator("[data-member] button").count()
    cut = sum("its ancestor div.verdict" in entry for entry in ring["clipped"])
    print(f"negative control, overflow hidden on the verdict wrapper: outlines clipped by it="
          f"{cut} of {verdicts} verdict buttons")
    if cut != verdicts:
        failures.append("negative control: an outline clipped by its wrapper was not detected")
    # 4. The second reviewed defect: no room below, so the outline leaves the viewport.
    #    The property is set through the CSSOM; the policy refuses a style attribute.
    for width in (1440, 390):
        size(page, width, "dark")
        page.evaluate("() => { document.documentElement.style.scrollPaddingBottom = '0px'; }")
        ring = clipping(page)
        page.evaluate("() => { document.documentElement.style.scrollPaddingBottom = ''; }")
        below = sum("the viewport's bottom" in entry for entry in ring["clipped"])
        print(f"negative control, no scroll padding below ({width}px): outlines past the viewport's "
              f"bottom={below}")
        if not below:
            failures.append(f"negative control: an outline past the viewport's bottom was not detected at {width}px")
    # 5. No room above: walking backward, a control comes in under the sticky heading.
    size(page, 390, "dark")
    page.evaluate("() => { document.documentElement.style.scrollPaddingTop = '0px'; }")
    ring = clipping(page, backward=True)
    page.evaluate("() => { document.documentElement.style.scrollPaddingTop = ''; }")
    covered = sum("a sticky" in entry for entry in ring["clipped"])
    print(f"negative control, no scroll padding above (390px, Shift+Tab): outlines under the sticky "
          f"heading={covered}")
    if not covered:
        failures.append("negative control: an outline under the sticky heading was not detected")
    size(page, 1440, "dark")
    after = clipping(page)
    if after["clipped"]:
        failures.append("negative control: the page was not restored")


def main() -> int:
    failures: list[str] = []
    if not (AXE / "axe.min.js").is_file():
        print("FAIL: axe-core is not installed; run `npm ci` in spikes/issue-210/frontend")
        return 1
    version = json.loads((AXE / "package.json").read_text(encoding="utf-8"))
    print(f"axe-core {version['version']} ({version['license']}), development-only")
    source = (AXE / "axe.min.js").read_text(encoding="utf-8")
    with harness.chromium() as browser:
        print("-- S13's seven states, synthetic fixture --")
        with harness.live_spike() as live:
            context = harness.authenticated_context(browser, live)
            harness.upload(context, live, "armor_close.csv")
            page = harness.open_slice(context, live)
            page.evaluate(source + "\n;undefined")
            run(page, "reviewing, unreviewed", failures)
            held = hold_one(page)
            harness.verdict_button(page, "6032", "Approve").click()
            while not held:
                page.wait_for_timeout(20)
            run(page, "approval in flight", failures)
            held[0][0].fulfill(response=held[0][1])
            harness.wait_status(page, "recorded your approval")
            page.unroute("**/api/verdicts")
            run(page, "reviewing, one approval", failures)
            harness.verdict_button(page, "6032", "Veto").click()
            harness.wait_status(page, "recorded your veto")
            run(page, "reviewing, one veto", failures)
            page.locator("[data-kind-filter=exact]").click()
            page.locator("select[data-facet=guardian_class]").select_option("Titan")
            page.locator("[data-kind-filter=same_stat]").click()
            run(page, "filtered", failures)
            page.get_by_role("button", name="Finalise review").click()
            harness.wait_status(page, "Finalised")
            run(page, "finalised", failures)
            page.get_by_role("button", name="Reset session").click()
            harness.wait_status(page, "reset")
            run(page, "no report", failures)
            context.close()
        print("-- the sanitised report --")
        with harness.live_spike() as live:
            preload(live, "real")
            context = harness.authenticated_context(browser, live)
            page = harness.open_slice(context, live)
            page.wait_for_selector("article[data-group]")
            page.evaluate(source + "\n;undefined")
            run(page, "sanitised report, unreviewed", failures)
            page.locator("[data-member] button").first.click()
            harness.wait_status(page, "recorded your approval")
            run(page, "sanitised report, one approval", failures)
            negative_controls(page, failures)
            context.close()
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
