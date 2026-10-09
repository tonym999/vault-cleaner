"""Deferred-rendering proof: viewport steps, total work, geometry, keyboard, axe.

Fresh pages measure navigation and one traversal each. Long Task entries are
observed in-page; none may overlap a slice scrolling step. No run or step is
excluded. Baseline accessibility counts use fixed #206 assets, same report.
"""

from __future__ import annotations

import sys

from run_proof import configure

configure()
from dev import preload
from expected import expected_groups
from harness import (
    authenticated_context,
    chromium,
    finish,
    live_spike,
    report,
    verdict_button,
)
from proof_gate import SETTLED_JS, TIMING_JS, TWO_FRAMES
from proof_s13_axe import AXE, RUN_JS
from proof_s15_scale import far_member
from proof_visual import baseline_assets

LONG_TASK_JS = """
window.__longTasks = [];
new PerformanceObserver(list => {
  __longTasks.push(...list.getEntries().map(entry => ({start: entry.startTime, duration: entry.duration})));
}).observe({type: 'longtask', buffered: true});
undefined;
"""
STEP_JS = """
y => new Promise(resolve => {
  const start = performance.now();
  window.scrollTo(0, y);
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const end = performance.now();
    setTimeout(() => resolve({start, end, elapsed: end - start, scroll: scrollY,
      height: document.documentElement.scrollHeight,
      tasks: __longTasks.filter(task => task.start < end && task.start + task.duration > start),
    }), 0);
  }));
})
"""
COVERAGE_JS = """
async () => {
  const result = await axe.run(document, {resultTypes: ['passes', 'violations', 'incomplete', 'inapplicable']});
  const nodes = new Set();
  const groups = new Set();
  for (const entries of [result.passes, result.violations, result.incomplete]) {
    for (const entry of entries) for (const node of entry.nodes) {
      const selector = node.target.join(' ');
      nodes.add(selector);
      const group = document.querySelector(selector)?.closest('article[data-group]');
      if (group) groups.add(group.getAttribute('data-group'));
    }
  }
  return {nodes: nodes.size, groups: groups.size, violations: result.violations.length};
}
"""


def traversal(context, live, name: str) -> dict:
    page = context.new_page()
    page.goto(live.origin + ("/spike/" if name == "slice" else "/"), wait_until="domcontentloaded")
    page.wait_for_function("() => __settled.navigation !== null")
    selector = 'article[data-group]' if name == 'slice' else '#vc-duplicate-list article.armor-group'
    before = page.evaluate("""selector => {
      window.__mid = document.querySelectorAll(selector)[37];
      return {height: document.documentElement.scrollHeight, top: __mid.getBoundingClientRect().top, scroll: scrollY};
    }""", selector)
    nav = page.evaluate("() => __settled.navigation")
    steps = []
    y = 0
    while True:
        step = page.evaluate(STEP_JS, y)
        steps.append(step)
        if step["scroll"] + 1000 >= step["height"] - 1:
            break
        y = step["scroll"] + 1000
        assert len(steps) < 300, "traversal did not terminate"
    page.evaluate(STEP_JS, before["scroll"])
    after = page.evaluate("""() => ({height: document.documentElement.scrollHeight,
      top: __mid.getBoundingClientRect().top, scroll: scrollY})""")
    bad_steps = [i + 1 for i, step in enumerate(steps) if step["tasks"]]
    total = sum(s["elapsed"] for s in steps)
    largest = max(s["elapsed"] for s in steps)
    print(f"{name} traversal: steps={len(steps)}; largest={largest:.1f}ms; total={total:.1f}ms; "
          f"steps with Long Task >50ms={bad_steps}; navigation={nav:.1f}ms; "
          f"navigation+traversal={nav + total:.1f}ms")
    print(f"{name} geometry: height before={before['height']} after={after['height']}; "
          f"mid-page element viewport top before={before['top']:.1f}px after={after['top']:.1f}px; "
          f"scroll before={before['scroll']} after={after['scroll']}")
    page.close()
    return {"bad": bad_steps, "before": before, "after": after}


def accessibility(context, live) -> bool:
    results = []
    for baseline in (True, False):
        page = context.new_page()
        if baseline:
            baseline_assets(page)
        page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        # Like S15, first read every required value/box, then make a full Tab
        # lap. These are the exact preconditions of its unchanged axe call.
        from harness import read_slice
        from proof_s6_layout import tab_through

        assert len(read_slice(page)["groups"]) == 74
        stops = tab_through(page)
        assert len(stops) == 444
        page.evaluate((AXE / "axe.min.js").read_text(encoding="utf-8") + "\n;undefined")
        per_scheme = []
        for scheme in ("light", "dark"):
            page.emulate_media(color_scheme=scheme)
            page.mouse.move(0, 0)
            page.wait_for_timeout(300)
            coverage = page.evaluate(COVERAGE_JS)
            contrast = page.evaluate(RUN_JS)
            per_scheme.append((coverage, contrast["incomplete"], len(contrast["measured"])))
            print(f"{'#206' if baseline else '#209'} axe {scheme}: unique targets={coverage['nodes']}; "
                  f"groups examined={coverage['groups']}; violations={coverage['violations']}; "
                  f"contrast incomplete={contrast['incomplete']}, measured={len(contrast['measured'])}; "
                  f"controls reached={len(stops)}")
        results.append(per_scheme)
        page.close()
    equal = results[0] == results[1]
    print(f"S15 axe/contrast coverage identical to #206={equal}")
    return equal


def main() -> int:
    if sys.argv[1:]:
        print("RESULT: FAIL (no arguments accepted)")
        return 1
    failures = []
    with live_spike() as live, chromium() as browser:
        preload(live, "real")
        context = authenticated_context(browser, live)
        context.add_init_script("window.__scaleGroups = 74;\n" + TIMING_JS + SETTLED_JS + LONG_TASK_JS)
        for name in ("slice", "production"):
            result = traversal(context, live, name)
            if name == "slice" and result["bad"]:
                failures.append("slice scrolling has a Long Task")
            if name == "slice" and any(
                abs(result["before"][key] - result["after"][key]) > 1
                for key in ("height", "top", "scroll")
            ):
                failures.append("slice document geometry changed across traversal (>1px)")
        page = context.new_page()
        page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        groups = expected_groups(report(context, live))
        _, _, member = far_member(groups)
        # Shift+Tab from the first stop wraps to the last native control.
        page.locator('a[href="#vc-title"]').focus()
        presses = 0
        for _ in range(3):
            page.keyboard.press("Shift+Tab")
            presses += 1
            page.evaluate(TWO_FRAMES)
            # Chromium has one outside-document BODY stop; S6 skips it too.
            if page.evaluate("() => document.activeElement !== document.body"):
                break
        last = verdict_button(page, member["id"], "Unset")
        focused = last.evaluate("node => node === document.activeElement")
        rendered = last.evaluate("""node => {
          const box = node.getBoundingClientRect();
          const group = node.closest('article[data-group]');
          return {visible: box.top >= 0 && box.bottom <= innerHeight,
            controls: group.querySelectorAll('button').length,
            boxes: Array.from(group.querySelectorAll('[data-member], [data-field]')).every(n => n.getBoundingClientRect().height > 0)};
        }""")
        print(f"keyboard jump to last control: Shift+Tab presses={presses}; focused={focused}; visible={rendered['visible']}; "
              f"group fully rendered={rendered['boxes']}; group controls={rendered['controls']}")
        if not focused or not rendered["visible"] or not rendered["boxes"]:
            failures.append("keyboard jump did not render/focus last group")
        page.close()
        if not accessibility(context, live):
            failures.append("axe/contrast coverage changed")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit as error:
        if error.code not in (None, 0):
            print("RESULT: FAIL (proof exited before completion)", flush=True)
        raise
    except Exception:
        print("RESULT: FAIL (proof raised an exception)", flush=True)
        raise
    sys.exit(code)
